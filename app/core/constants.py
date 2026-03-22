
 
APP_TITLE       = "SmartChat API"
APP_VERSION     = "1.0.0"
APP_DESCRIPTION = "SmartChat FastAPI Backend"
 
GEMINI_MODEL    = "gemini-2.5-flash"
 
MEDIA_DIR            = "media"
CHAT_FILES_SUBDIR    = "chat_files"
CHAT_FILES_DIR       = f"{MEDIA_DIR}/{CHAT_FILES_SUBDIR}"

 
DEFAULT_CHAT_TITLE  = "New Chat"

 
CONTENT_TYPE_IMAGE      = "image/"
CONTENT_TYPE_TEXT       = "text/"
CONTENT_TYPE_PDF        = "application/pdf"
 
PROMPT_DESCRIBE_IMAGE   = "Describe this image in detail."
PROMPT_ANALYZE_FILE     = "Please analyze this file content."
PROMPT_ACKNOWLEDGE_FILE = "Please acknowledge the file."
PROMPT_FILE_PREFIX      = "File content ({filename}):\n\n{content}\n\n"
PROMPT_FILE_QUESTION    = "User question: {question}"
PROMPT_OTHER_FILE       = "User uploaded a file: {filename} ({file_type})\n\n"
 
ERROR_INVALID_GOOGLE_TOKEN      = "Invalid Google token"
ERROR_USER_ALREADY_EXISTS       = "User already exists"
ERROR_INVALID_CREDENTIALS       = "Invalid email or password"
ERROR_COULD_NOT_VALIDATE        = "Could not validate credentials"
ERROR_CHAT_NOT_FOUND            = "Chat not found"
ERROR_MESSAGE_NOT_FOUND         = "Message not found"
ERROR_INVALID_JSON              = "Invalid JSON body"
ERROR_INVALID_FORM              = "Invalid form data: {detail}"
ERROR_MESSAGE_OR_FILE_REQUIRED  = "Message or file required"
ERROR_UNSUPPORTED_CONTENT_TYPE  = "Content-Type must be application/json or multipart/form-data"
 
STATUS_HEALTHY      = "healthy"
REFRESH_TOKEN ="refresg_token"
EMAIL = "email"
NAME =  "name"
GOOGLE_ID ="google_id"
PICTURE = "picture"
ACCESS_TOKEN = "access_token"

 
 
BCRYPT_SCHEMES      = ["bcrypt"]
BCRYPT_DEPRECATED   = "auto"
PASSWORD_MAX_LEN    = 72        
OAUTH2_TOKEN_URL    = "/login"

# Session rate limiting
SESSION_LIMIT       = 100
EXPIRY_SECONDS      = 432000  # 120 hours

 
CORS_ORIGINS        = ["http://localhost:3000", "http://localhost", "https://localhost"]
CORS_METHODS        = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_HEADERS        = ["Content-Type", "Authorization"]

 
STREAM_CHUNK        = "chunk"
STREAM_DONE         = "done"
STREAM_ERROR        = "error"

 
FEEDBACK_LIKE       = "like"
FEEDBACK_DISLIKE    = "dislike"
INVALID_FEEDBACK    ="Invalid feedback value"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K=5
class RESPONSE_MESSAGE:
    LOGIN_SUCCESS = "Login successful"
    GOOGLE_LOGIN_SUCCESS = "Google login successful"
    REGISTER_SUCCESS = "Registration successful"
    TOKEN_REFRESH_SUCCESS = "Token refreshed successfully"
    CHAT_CREATED = "Chat created successfully"
    CHAT_UPDATED = "Chat updated successfully"
    CHAT_DELETED = "Chat deleted successfully"
    MESSAGE_SENT = "Message sent successfully"
    MESSAGE_UPDATED = "Message updated successfully"
    FEEDBACK_ADDED = "Feedback added successfully"
    CHATS_RETRIEVED = "Chats retrieved successfully"
    MESSAGES_RETRIEVED = "Messages retrieved successfully"