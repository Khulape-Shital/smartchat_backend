from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import asyncio
import pathlib
from uuid import UUID
import logging
from app.core.time_utils import get_unix_timestamp
from google import genai
import google.generativeai as genai
from google.genai import types
import PyPDF2
from io import BytesIO
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from app.db.session import get_db, SessionLocal
from app.models.user import User
from app.models.chat import ChatSession, Message, DocumentChunk
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionUpdate,
    MessageResponse, MessageFeedback, MessageCreate
)
from app.core.security import get_current_user
from app.core.config import settings
from app.core.constants import (
    GEMINI_MODEL, MEDIA_DIR, CHAT_FILES_SUBDIR, CHAT_FILES_DIR, DEFAULT_CHAT_TITLE,
    CONTENT_TYPE_IMAGE, CONTENT_TYPE_TEXT, CONTENT_TYPE_PDF,
    PROMPT_DESCRIBE_IMAGE, PROMPT_ANALYZE_FILE, PROMPT_ACKNOWLEDGE_FILE,
    PROMPT_FILE_PREFIX, PROMPT_FILE_QUESTION, PROMPT_OTHER_FILE,
    ERROR_CHAT_NOT_FOUND, ERROR_MESSAGE_NOT_FOUND, ERROR_MESSAGE_OR_FILE_REQUIRED,
    ERROR_UNSUPPORTED_CONTENT_TYPE, ERROR_INVALID_JSON, ERROR_INVALID_FORM,
    STREAM_CHUNK, STREAM_DONE, STREAM_ERROR, RESPONSE_MESSAGE,
    FEEDBACK_LIKE, FEEDBACK_DISLIKE, INVALID_FEEDBACK
)
from app.utils.rag import retrieve_chunks, store_chunks
from app.middleware.middleware import session_limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()

client = genai.Client(api_key=settings.GEMINI_API_KEY)
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

# Background task function for title generation
def generate_chat_title_background(
    chat_id: UUID,
    user_text: str,
    file_name: Optional[str],
    db: Session
):
    """
    Generate and save chat title in the background after streaming response.
    Prevents blocking the STREAM_DONE event on the Gemini API latency.
    """
    try:
        # Prepare message for title generation
        message_preview = user_text[:300].strip() if user_text else f'File: {file_name}' if file_name else 'New Chat'
        
        title_prompt = f"""Create a brief, descriptive title (3-7 words max) that summarizes the main topic or intent.
Keep it clear, specific, and concise. Return ONLY the title text, nothing else.

Message: {message_preview}

Title:"""

        logger.debug(f"Generating title for chat {chat_id}")
        
        title_response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=title_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=50,
            )
        )

        generated_title = ""
        if hasattr(title_response, 'text') and title_response.text:
            # Clean the response
            generated_title = title_response.text.strip()
            
            # Remove quotes, asterisks, and markdown formatting
            for char in ['"', "'", '*', '#', '_', '`']:
                generated_title = generated_title.replace(char, '')
            
            generated_title = generated_title.strip().strip('.')
            
            # Validate word count (3-7 words)
            word_count = len(generated_title.split())
            if word_count < 3 or word_count > 7:
                logger.warning(f"Generated title has {word_count} words, expected 3-7: {generated_title}")

        # Validation: ensure title is reasonable
        if not generated_title or len(generated_title) > 100:
            logger.warning(f"Invalid title generated: '{generated_title}'. Using fallback.")
            # Fallback: create title from first words of message
            if user_text and len(user_text.strip()) > 0:
                words = user_text.strip().split()[:7]  # First 7 words max
                generated_title = " ".join(words)
                if len(user_text.strip()) > len(generated_title):
                    generated_title += "..."
            elif file_name:
                generated_title = file_name[:50].strip()
            else:
                generated_title = DEFAULT_CHAT_TITLE

        # Update session with generated title
        session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if session:
            session.title = generated_title
            db.commit()
            logger.info(f"✅ Chat title updated: {chat_id} -> '{generated_title}'")
        else:
            logger.error(f"Chat session not found: {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Background title generation failed for chat {chat_id}: {str(e)}")
        # Don't raise - background tasks should not crash the stream
        # Title will remain as DEFAULT_CHAT_TITLE

@router.get("/chats", response_model=List[ChatSessionResponse])
async def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.created_at.desc()).offset(skip).limit(limit).all()

    return sessions

@router.post("/chats", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    title = (chat_data.title or DEFAULT_CHAT_TITLE).strip()

    session = ChatSession(
        user_id=current_user.id,
        title=title
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session

@router.put("/chats/{chat_id}", response_model=ChatSessionResponse)
async def update_chat(
    chat_id: UUID,
    chat_data: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.id == chat_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_CHAT_NOT_FOUND
        )

    if chat_data.title:
        session.title = chat_data.title.strip()
        session.updated_at = get_unix_timestamp()

        db.commit()
        db.refresh(session)

    return session

@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_CHAT_NOT_FOUND
        )
      
    db.delete(session)
    db.commit()


@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_CHAT_NOT_FOUND
        )

    messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at).all()

    return messages

 
@limiter.limit("3/minute") 
@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Apply session rate limiting
    session_limiter(str(chat_id))
    
    session = db.query(ChatSession).filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_CHAT_NOT_FOUND
        )
    
    user_text = ""
    file = None

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            user_text = (body.get("message") or "").strip()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_INVALID_JSON
            )

    elif "multipart/form-data" in content_type:
        try:
            form_data = await request.form()
            user_text = (form_data.get("message") or "").strip()      
            file = form_data.get("file")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_INVALID_FORM.format(detail=str(e))
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_UNSUPPORTED_CONTENT_TYPE
        )
    
    if not user_text and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGE_OR_FILE_REQUIRED
        )
    
    # Limit history to the last 20 messages for efficiency and context window limits
    existing_messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.desc()).limit(20).all()
    
    # Reverse to get chronological order for Gemini history
    existing_messages = list(reversed(existing_messages))

    gemini_history=[]

    for m in existing_messages:
        if m.role=="user":
            gemini_history.append(
                 types.Content(role="user",parts=[types.Part(text= m.message)])
              )
        
            if m.ai_response:
                gemini_history.append(
                    types.Content(role="model", parts=[types.Part(text=m.ai_response)])
                )    

    async def stream_response():
        # Create a fresh database session for the streaming operation
        stream_db = SessionLocal()
        full_response = []
        message_id = None
        file_path = None

        try:
            content_parts = []

            # =========================
            #  FILE HANDLING
            # =========================
            if file:
                file_type = file.content_type
                os.makedirs(CHAT_FILES_DIR, exist_ok=True)

                # Sanitize filename to prevent path traversal
                safe_filename = pathlib.Path(file.filename).name
                file_name = f"{get_unix_timestamp()}_{safe_filename}"
                file_path = f"{CHAT_FILES_SUBDIR}/{file_name}"
                full_file_path = os.path.join(MEDIA_DIR, file_path)

                file_content = await file.read()

                # Check file size limit (100MB)
                MAX_FILE_BYTES = 100 * 1024 * 1024
                if len(file_content) > MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size exceeds {MAX_FILE_BYTES // (1024*1024)}MB limit"
                    )

                with open(full_file_path, "wb") as f:
                    f.write(file_content)

                text_content = ""   # RAG

                if file_type and file_type.startswith(CONTENT_TYPE_IMAGE):
                    content_parts.append(types.Part.from_bytes(data=file_content, mime_type=file_type))
                    if user_text:
                        content_parts.append(types.Part(text=user_text))
                    else:
                        content_parts.append(types.Part(text=PROMPT_DESCRIBE_IMAGE))

                elif file_type and file_type.startswith(CONTENT_TYPE_TEXT):
                    text_content = file_content.decode('utf-8', errors='ignore')

                    # Use asyncio.to_thread to avoid blocking the event loop
                    if text_content.strip():
                        await asyncio.to_thread(store_chunks, stream_db, str(chat_id), str(current_user.id), text_content)

                    prompt = PROMPT_FILE_PREFIX.format(filename=file.filename, content=text_content)

                    if user_text:
                        prompt += PROMPT_FILE_QUESTION.format(question=user_text)
                    else:
                        prompt += PROMPT_ANALYZE_FILE

                    content_parts.append(prompt)

                elif file_type and file_type == CONTENT_TYPE_PDF:
                    try:
                        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                        text_content = ""
                        for page_num in range(len(pdf_reader.pages)):
                            page = pdf_reader.pages[page_num]
                            text_content += f"\n--- Page {page_num + 1} ---\n"
                            text_content += page.extract_text()

                        # Use asyncio.to_thread for blocking embedding call
                        if text_content.strip():
                            await asyncio.to_thread(store_chunks, stream_db, str(chat_id), str(current_user.id), text_content)

                        if not text_content.strip():
                            text_content = "[PDF content could not be extracted.]"

                        prompt = PROMPT_FILE_PREFIX.format(filename=file.filename, content=text_content)

                        if user_text:
                            prompt += PROMPT_FILE_QUESTION.format(question=user_text)
                        else:
                            prompt += PROMPT_ANALYZE_FILE

                        content_parts.append(prompt)

                    except Exception as pdf_error:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Error reading PDF file: {str(pdf_error)}"
                        )

                else:
                    prompt = PROMPT_OTHER_FILE.format(filename=file.filename, file_type=file.content_type)

                    if user_text:
                        prompt += user_text
                    else:
                        prompt += PROMPT_ACKNOWLEDGE_FILE

                    content_parts.append(prompt)

            # If no file was attached, use user_text as the content with RAG context if available
            if not file and user_text:
                # [OPTIMIZATION] Retrieve relevant context from vector database if documents exist
                rag_context = ""
                try:
                    relevant_chunks = await asyncio.to_thread(
                        retrieve_chunks,
                        stream_db,
                        str(chat_id),
                        str(current_user.id),
                        user_text,
                        TOP_K=3  # Get top 3 most relevant chunks
                    )

                    if relevant_chunks:
                        rag_context = "\n\n---\nRelevant Context from Documents:\n" + "\n---\n".join(relevant_chunks)
                        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for RAG context")

                except Exception as e:
                    logger.warning(f"RAG context retrieval failed (non-fatal): {e}")
                    rag_context = ""

                # Combine RAG context with user question
                final_text = f"{rag_context}\n\nUser Question: {user_text}" if rag_context else user_text
                content_parts.append(types.Part(text=final_text))

            # Handle content based on number of parts
            if len(content_parts) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGE_OR_FILE_REQUIRED
                )
            elif len(content_parts) == 1:
                contents = content_parts[0]
            else:
                contents = content_parts
            # =========================
            #  GEMINI CALL
            # =========================
            if gemini_history:
                chat_session = client.chats.create(model=GEMINI_MODEL, history=gemini_history)
                response = chat_session.send_message_stream(contents)
            else:
                response = client.models.generate_content_stream(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        top_p=0.9,
                        top_k=40,
                        max_output_tokens=2000,
                    ))

            for chunk in response:
                if chunk.text:
                    full_response.append(chunk.text)
                    yield f"data: {json.dumps({'type': STREAM_CHUNK, 'text': chunk.text})}\n\n"

            ai_reply = "".join(full_response)

            user_msg = Message(
                chat_id=chat_id,
                role="user",
                message=user_text or f"[Uploaded file: {file.filename}]",
                ai_response=ai_reply,
                file=file_path if file else None,
                file_name=file.filename if file else None,
                file_type=file.content_type if file else None
            )

            stream_db.add(user_msg)
            stream_db.commit()
            stream_db.refresh(user_msg)

            message_id = str(user_msg.id)

            # Update session
            session = stream_db.query(ChatSession).filter(
                ChatSession.id == chat_id,
                ChatSession.user_id == current_user.id
            ).first()
            
            if session:
                session.updated_at = get_unix_timestamp()

                if not existing_messages:
                    background_tasks.add_task(
                        generate_chat_title_background,
                        chat_id=chat_id,
                        user_text=user_text,
                        file_name=file.filename if file else None,
                        db=stream_db
                    )
                    session.title = DEFAULT_CHAT_TITLE

                stream_db.commit()

            yield f"data: {json.dumps({'type': STREAM_DONE, 'message_id': message_id})}\n\n"

        except Exception as exc:
            error_message = str(exc)

            if "429" in error_message or "quota" in error_message.lower():
                error_message = "API quota exceeded."

            yield f"data: {json.dumps({'type': STREAM_ERROR, 'error': error_message})}\n\n"
        
        finally:
            stream_db.close()
    

    return StreamingResponse(
         stream_response(),
         media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

 
@router.post("/messages/{message_id}/feedback", response_model=MessageResponse)
async def add_feedback(
    message_id: UUID,
    feedback_data: MessageFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add or update feedback for a message.
    """
    message = db.query(Message).join(ChatSession).filter(
        Message.id == message_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGE_NOT_FOUND
        )
    
    message.feedback = feedback_data.feedback
    message.updated_at = get_unix_timestamp()
    db.commit()
    db.refresh(message)
    
    return message





@router.put("/messages/{message_id}/edit")
async def edit_message(
    message_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Edit a user message and regenerate AI response with streaming.
    Supports both JSON request bodies and form-data.
    """
    message = db.query(Message).join(ChatSession).filter(
        Message.id == message_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGE_NOT_FOUND
        )
    
    if message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit user messages"
        )
    
    # Parse request based on content-type
    message_text = ""
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            message_text = (body.get("message") or "").strip()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_INVALID_JSON
            )
    elif "multipart/form-data" in content_type:
        try:
            form_data = await request.form()
            message_text = (form_data.get("message_text") or form_data.get("message") or "").strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_INVALID_FORM.format(detail=str(e))
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_UNSUPPORTED_CONTENT_TYPE
        )
    
    new_text = message_text
    
    if not new_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )
    
    # Build conversation history up to this message
    chat_session = message.chat
    all_messages = db.query(Message).filter(
        Message.chat_id == chat_session.id,
        Message.created_at < message.created_at
    ).order_by(Message.created_at).all()
    
    gemini_history = []
    for m in all_messages:
        if m.role == "user":
            gemini_history.append(
                types.Content(role="user", parts=[types.Part(text=m.message)])
            )
            if m.ai_response:
                gemini_history.append(
                    types.Content(role="model", parts=[types.Part(text=m.ai_response)])
                )
    
    async def stream_edit_response():
        # Create a fresh database session for the streaming operation
        stream_db = SessionLocal()
        full_response = []

        try:
            # Re-fetch the message with the new session
            message_to_edit = stream_db.query(Message).join(ChatSession).filter(
                Message.id == message_id,
                ChatSession.user_id == current_user.id
            ).first()

            if not message_to_edit:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGE_NOT_FOUND
                )

            if gemini_history:
                chat = client.chats.create(model=GEMINI_MODEL, history=gemini_history)
                response = chat.send_message_stream(new_text)
            else:
                response = client.models.generate_content_stream(
                    model=GEMINI_MODEL,
                    contents=new_text,
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        top_p=0.9,
                        top_k=40,
                        max_output_tokens=2000,
                    )
                )

            # Stream chunks
            for chunk in response:
                if chunk.text:
                    full_response.append(chunk.text)
                    yield f"data: {json.dumps({'type': STREAM_CHUNK, 'text': chunk.text})}\n\n"

            # Update message
            ai_reply = "".join(full_response)
            message_to_edit.message = new_text
            message_to_edit.ai_response = ai_reply
            message_to_edit.updated_at = get_unix_timestamp()
            stream_db.commit()

            yield f"data: {json.dumps({'type': STREAM_DONE, 'message_id': str(message_to_edit.id)})}\n\n"

        except Exception as exc:
            error_message = str(exc)

            if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
                error_message = "API quota exceeded. You've reached the daily limit for the Gemini API."

            yield f"data: {json.dumps({'type': STREAM_ERROR, 'error': error_message})}\n\n"

        finally:
            stream_db.close()
    
    return StreamingResponse(
        stream_edit_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )



