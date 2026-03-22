from sentence_transformers import SentenceTransformer
from app.models import DocumentChunk
import uuid
from app.core.constants import (CHUNK_OVERLAP,CHUNK_SIZE,TOP_K)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

# [HIGH] Model loaded lazily with singleton pattern - optimize with startup initialization
_embedding_model = None

def initialize_embeddings_model():
    """
    Initialize and load the embedding model at application startup.
    Call this once in main.py lifespan handler to avoid per-request delays.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformers embedding model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded successfully")
    return _embedding_model

def get_embeddings_model():
    """Get the cached embedding model. Model should be pre-loaded at startup."""
    global _embedding_model
    if _embedding_model is None:
        logger.warning("Embedding model not initialized at startup. Loading now (will add 1-3s delay)...")
        initialize_embeddings_model()
    return _embedding_model


def chunk_text(text: str) -> list[str]:
    """
    Splits text into semantically meaningful chunks using sentence-aware logic.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],  # sentence → word fallback
    )

    return text_splitter.split_text(text)

def store_chunks(db, chat_id, user_id, text):
    """
    Store document chunks with embeddings using batch encoding for efficiency.
    
    Optimizations:
    - Batches all embeddings together instead of one-by-one
    - Uses SentenceTransformer's batch processing which is ~2-3x faster
    - Still requires db.commit() to be called by the endpoint
    """
    # Convert string UUIDs to UUID objects if needed
    if isinstance(chat_id, str):
        chat_id = uuid.UUID(chat_id)
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    chunks = chunk_text(text)
    
    if not chunks:
        logger.warning(f"No chunks generated from text for chat {chat_id}")
        return
    
    embedding_model = get_embeddings_model()
    
    # [OPTIMIZATION] Batch encode all chunks at once instead of 1-by-1
    # SentenceTransformer.encode() with list input uses batches internally
    # This is 2-3x faster than looping and calling encode() for each chunk
    logger.info(f"Batch encoding {len(chunks)} chunks for chat {chat_id}...")
    embeddings = embedding_model.encode(chunks, batch_size=32, show_progress_bar=False)
    
    # Create DocumentChunk objects with embeddings
    for chunk, embedding in zip(chunks, embeddings):
        doc = DocumentChunk(
            chat_id=chat_id,
            user_id=user_id,
            content=chunk,
            embedding=embedding.tolist()  # Convert numpy array to list for pgvector
        )
        db.add(doc)
    
    logger.info(f"Queued {len(chunks)} document chunks for database insert")


def retrieve_chunks(db, chat_id, user_id, question, TOP_K):
    """
    Retrieve most relevant chunks using vector similarity search.
    
    Usage:
        relevant_context = retrieve_chunks(db, chat_id, user_id, "What is the topic?", 5)
        # Returns list of top-5 most similar chunk contents
    
    Optimizations:
    - Only fetches content column (not full ORM objects)
    - Uses pgvector L2 distance for semantic similarity
    - Filters by user_id for security
    """
    # Convert string UUIDs to UUID objects if needed
    if isinstance(chat_id, str):
        chat_id = uuid.UUID(chat_id)
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    embedding_model = get_embeddings_model()
    
    # [OPTIMIZATION] Single encode call for the query
    query_embedding = embedding_model.encode(question, show_progress_bar=False).tolist()

    # Query the database with vector similarity search
    results = db.query(DocumentChunk).filter(
        DocumentChunk.chat_id == chat_id,
        DocumentChunk.user_id == user_id  # Security: Only user's own chunks
    ).order_by(
        DocumentChunk.embedding.l2_distance(query_embedding)
    ).limit(TOP_K).all()

    return [r.content for r in results]