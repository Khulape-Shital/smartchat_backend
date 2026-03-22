# SmartChat Backend

A powerful, production-ready AI chat backend built with **FastAPI**, **PostgreSQL**, and **Google Gemini API**. Features real-time streaming responses, file processing, RAG (Retrieval Augmented Generation), user authentication, and email verification.

 
## 🚀 Features

- ✅ **Streaming Chat API** - Real-time responses with Server-Sent Events (SSE)
- ✅ **File Upload & Processing** - Images, PDFs, text files with RAG
- ✅ **Email Verification** - Secure registration with email verification
- ✅ **Password Reset** - Email-based password recovery
- ✅ **Google OAuth** - Sign in with Google
- ✅ **JWT Authentication** - Secure token-based auth with refresh tokens
- ✅ **Rate Limiting** - Per-user and per-session rate limiting
- ✅ **RAG (Vector Search)** - Retrieve relevant document chunks for queries
- ✅ **Message Feedback** - Track user feedback (like/dislike)
- ✅ **Chat Sessions** - Organize chats with automatic title generation
- ✅ **Async/Await** - Non-blocking operations for better performance
- ✅ **Database Migrations** - Alembic for schema management
- ✅ **Comprehensive Logging** - Debug and production logging

## 📋 Tech Stack

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Modern async web framework |
| **SQLAlchemy 2.0** | ORM for database operations |
| **PostgreSQL** | Primary database |
| **Alembic** | Database migrations |
| **PyJWT** | JWT token generation/validation |
| **Google Gemini API** | AI model for chat responses |
| **SentenceTransformers** | Embeddings for RAG |
| **Pinecone/FAISS** | Vector database for embeddings |
| **PyPDF2** | PDF file processing |
| **Pydantic** | Data validation |
| **Slowapi** | Rate limiting |
| **SMTP** | Email verification & password reset |

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── api.py              # Main API router
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py     # Authentication endpoints
│   │           └── chat.py     # Chat endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Settings & environment variables
│   │   ├── constants.py        # App-wide constants
│   │   ├── security.py         # JWT & password hashing
│   │   └── time_utils.py       # Timestamp utilities
│   ├── db/
│   │   ├── __init__.py
│   │   ├── init_db.py          # Database initialization
│   │   ├── session.py          # Database session management
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── middleware.py       # CORS, rate limiting, custom middleware
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # User model
│   │   ├── chat.py             # ChatSession & Message models
│   │   ├── email_verification.py
│   │   ├── password_reset.py
│   │   ├── token_blacklist.py
│   │   └── models.py           # Additional models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Pydantic schemas for users
│   │   └── chat.py             # Pydantic schemas for chat
│   ├── services/
│   │   ├── __init__.py
│   │   └── (custom services)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py          # Utility functions
│   │   └── rag.py              # RAG implementation
│   └── middleware/
│       └── middleware.py       # Rate limiting, custom middleware
├── alembic/
│   ├── versions/               # Migration files
│   ├── env.py                  # Alembic configuration
│   ├── script.py.mako         # Migration template
│   └── README                  # Alembic documentation
├── media/
│   └── chat_files/             # Uploaded files storage
├── tests/
│   └── test_auth.py            # Tests
├── .env                        # Environment variables (NOT in git)
├── alembic.ini                # Alembic configuration
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## ⚙️ Installation & Setup

### Prerequisites
- **Python 3.10+**
- **PostgreSQL 13+**
- **pip** or **poetry**
- **Google Gemini API Key** (free tier available)

### 1. Clone Repository

```bash
git clone <repo-url>
cd backend
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/smartchat_db

# Security
SECRET_KEY=your-super-secret-key-min-32-chars-long-change-in-production
ALGORITHM=HS256

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Gemini API
GEMINI_API_KEY=your_google_gemini_api_key_here

# Email Configuration (for verification & password reset)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
PASSWORD_RESET_EXPIRE_MINUTES=10

# Frontend URL
FRONTEND_URL=http://localhost:3000

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
CORS_ALLOW_CREDENTIALS=true

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id_here
```

**Important Security Notes:**
- Change `SECRET_KEY` to a random 32+ character string in production
- Use environment-specific `.env` files
- Never commit `.env` to version control

### 5. Create PostgreSQL Database

```bash
# Windows
psql -U postgres -c "CREATE DATABASE smartchat_db;"

# macOS/Linux
createdb smartchat_db
```

### 6. Run Database Migrations

```bash
alembic upgrade head
```

### 7. Start Development Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Server runs at `http://127.0.0.1:8000`

API docs at `http://127.0.0.1:8000/docs` (Swagger UI)

## 🔐 Authentication System

### Registration Flow
```
POST /api/v1/auth/register
├── Validate input (email, password, name)
├── Hash password with bcrypt
├── Create user in database
├── Generate email verification token
├── Send verification email
└── Return success message
```

### Email Verification
```
GET /api/v1/auth/verify-email?token=xxx
├── Decode verification token
├── Mark user as verified
└── User can now login
```

### Login Flow
```
POST /api/v1/auth/login
├── Validate email & password
├── Generate JWT access_token (30 min expiry)
├── Generate JWT refresh_token (7 day expiry)
└── Return tokens
```

### Token Refresh
```
POST /api/v1/auth/refresh
├── Validate refresh_token
├── Generate new access_token
└── Return new access_token
```

### Password Reset
```
POST /api/v1/auth/forgot-password
├── Send reset link via email

PUT /api/v1/auth/reset-password
├── Validate reset token
├── Hash new password
└── Update user password
```

## 💬 Chat API

### Create Chat Session
```
POST /api/v1/chat/chats
├── Create new ChatSession
├── Associate with current user
└── Return session details
```

### Send Message (Streaming)
```
POST /api/v1/chat/chats/{chat_id}/messages
├── Validate chat ownership
├── Process file (if attached)
├── Build conversation history
├── Call Gemini API with streaming
├── Stream: data: {"type": "chunk", "text": "..."}
├── Stream: data: {"type": "done", "message_id": "uuid"}
├── Generate chat title (background task)
└── Save message to database
```

**Request:**
```json
{
  "message": "What does this document say?",
  "file": <optional file>
}
```

**Response (Server-Sent Events):**
```
data: {"type": "chunk", "text": "The document "}
data: {"type": "chunk", "text": "contains..."}
data: {"type": "done", "message_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Edit Message (Streaming)
```
PUT /api/v1/chat/messages/{message_id}/edit
├── Validate message ownership & role
├── Build conversation history
├── Stream new response from Gemini
└── Update message in database
```

### Get Chat Messages
```
GET /api/v1/chat/chats/{chat_id}/messages
├── Validate chat ownership
└── Return all messages with latest first
```

### Message Feedback
```
POST /api/v1/chat/messages/{message_id}/feedback
├── Validate message ownership
├── Save feedback (like/dislike/null)
└── Return updated message
```

## 🔍 RAG (Retrieval Augmented Generation)

### How RAG Works

1. **Document Upload** → Extract text from file
2. **Chunking** → Split into smaller text segments
3. **Embedding** → Convert chunks to vector embeddings
4. **Storage** → Save embeddings with metadata
5. **Query** → Convert user query to embedding
6. **Search** → Find top-K similar chunks
7. **Augment** → Include chunks in Gemini prompt
8. **Generate** → Gemini gives grounded answer

### Supported File Types
- 📄 **PDF** - Extracted with PyPDF2
- 📝 **Text** - Encoded as UTF-8
- 🖼️ **Images** - Processed by Gemini vision
- 📊 **Other** - Saved for download/reference

### Store Embeddings
```python
from app.utils.rag import store_chunks

store_chunks(
    db=session,
    chat_id="chat_uuid",
    user_id="user_uuid",
    text_content="Document text here..."
)
```

### Retrieve Chunks
```python
from app.utils.rag import retrieve_chunks

chunks = retrieve_chunks(
    db=session,
    chat_id="chat_uuid",
    user_id="user_uuid",
    query="What does this say?",
    TOP_K=3  # Return top 3 most relevant chunks
)
```

## 🔒 Security Features

### Password Security
- Hashed with bcrypt (cost factor: 12)
- Never stored in plaintext
- Minimum 8 characters, mixed case, numbers required

### JWT Tokens
- Signed with HS256
- Includes user_id and exp (expiration)
- Short-lived access tokens (30 min)
- Long-lived refresh tokens (7 days)
- Tokens can be blacklisted

### Rate Limiting
- Per-route limit: 3 requests/minute
- Per-session limit: 10 requests/minute
- Returns 429 Too Many Requests

### CORS Protection
- Whitelist of allowed origins
- Credentials transmission controlled
- Prevents unauthorized cross-origin requests

### SQL Injection Prevention
- SQLAlchemy ORM (parameterized queries)
- Pydantic validation
- Input sanitization

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  name VARCHAR NOT NULL,
  hashed_password VARCHAR NOT NULL,
  is_verified BOOLEAN DEFAULT false,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  google_id VARCHAR UNIQUE
)
```

### ChatSessions Table
```sql
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY,
  user_id UUID FOREIGN KEY,
  title VARCHAR NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
)
```

### Messages Table
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY,
  chat_id UUID FOREIGN KEY,
  role VARCHAR (user/model),
  message TEXT NOT NULL,
  ai_response TEXT,
  feedback VARCHAR (like/dislike),
  file VARCHAR,
  file_name VARCHAR,
  file_type VARCHAR,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
)
```

## 🧪 Testing

### Run Tests
```bash
pytest tests/ -v
```

### Example Test
```python
def test_send_message(client, auth_headers, chat_id):
    response = client.post(
        f"/api/v1/chat/chats/{chat_id}/messages",
        json={"message": "Hello AI"},
        headers=auth_headers
    )
    assert response.status_code == 200
```

## 🚀 Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Using Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Config for Production
```env
# Use strong secret key
SECRET_KEY=generate-strong-key-here-min-32-chars

# Use production database
DATABASE_URL=postgresql://prod_user:prod_pass@prod-db.com:5432/smartchat

# Disable CORS for unsafe origins
CORS_ORIGINS=["https://yourdomain.com"]

# Enable HTTPS
CORS_ALLOW_CREDENTIALS=true

# Production logging
LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

### Issue: "No module named 'app'"
```bash
# Add backend directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: "Database connection refused"
- ✅ Verify PostgreSQL is running
- ✅ Check DATABASE_URL matches actual database
- ✅ Confirm credentials are correct

### Issue: "Email not sending"
- ✅ Enable "Less secure app access" in Gmail
- ✅ Use app-specific password (2FA enabled)
- ✅ Check SMTP credentials in `.env`

### Issue: "Streaming stops mid-response"
- ✅ Check database session is not closing early
- ✅ Verify `stream_db` is used in async generators
- ✅ Check for exceptions in logs

### Issue: "RAG not retrieving chunks"
- ✅ Verify embeddings are stored: `SELECT COUNT(*) FROM document_chunks;`
- ✅ Check vector database is initialized
- ✅ Ensure chunks are within similarity threshold

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org)
- [PostgreSQL](https://www.postgresql.org/docs)
- [Google Gemini API](https://ai.google.dev)
- [JWT.io](https://jwt.io)
- [Alembic Migrations](https://alembic.sqlalchemy.org)

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test
3. Run migrations: `alembic upgrade head`
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Create Pull Request

## 📄 License

MIT License - See LICENSE file for details
