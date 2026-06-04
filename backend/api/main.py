"""
FastAPI backend for the RAG chat system.
"""

from fastapi import FastAPI, HTTPException, Header, Request, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import sys
import os

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import RAGSystem, SimpleRAGSystem, VectorStore
from scraper import WebScraper
from api.query_logger import QueryLogger
from api.login_tracker import LoginTracker
from api.database_manager import DatabaseManager
from api.power_search import PowerSearchService
from api.user_manager import UserManager
from api.training_manager import TrainingSetManager
from api.training_run_tracker import TrainingRunTracker
import time
import shutil
from pathlib import Path

# Configuration
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Authentication configuration
WEB_AUTH_ENABLED = os.getenv("WEB_AUTH_ENABLED", "true").lower() == "true"
WEB_USERNAME = os.getenv("WEB_USERNAME", "demo")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "changeme")
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-this")

# PEFT adapter to use for the RAG generation backend. Configure via env var
# to point to your trained adapter; the default below is a placeholder.
PEFT_ADAPTER_PATH = os.getenv("PEFT_ADAPTER_PATH", "training/adapters/example")

# Site Access Gate configuration
SITE_PASSPHRASE = os.getenv("SITE_PASSPHRASE", "")  # Shared passphrase for community access

# Session serializer (24 hour expiry)
session_serializer = URLSafeTimedSerializer(SECRET_KEY)

# Gate token serializer (indefinite expiry for passphrase access)
gate_serializer = URLSafeTimedSerializer(SECRET_KEY + "_gate")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="RAG Chat API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency
async def verify_admin_key(x_api_key: Optional[str] = Header(None)):
    """Verify admin API key for protected endpoints."""
    if DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="This operation is disabled in demo mode"
        )
    if not ADMIN_API_KEY:
        return True  # No auth required if key not set
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Initialize database manager
db_manager = DatabaseManager(config_file="database_config.json")

# Initialize RAG system with PEFT adapter
# Use the active database path from database manager
active_db_path = db_manager.get_database_path()
rag_system = RAGSystem(
    llm_provider="peft",
    model_name=PEFT_ADAPTER_PATH,
    vector_store=VectorStore(persist_directory=active_db_path)
)

# Initialize query logger
query_logger = QueryLogger(log_dir="logs")

# Initialize login tracker (5 attempts, 15 minute lockout)
login_tracker = LoginTracker(max_attempts=5, lockout_duration=900)

# Initialize user manager
user_manager = UserManager()

# Initialize power search service
power_search = PowerSearchService()

# Initialize training set manager
training_manager = TrainingSetManager()

# Initialize training run tracker
training_run_tracker = TrainingRunTracker()

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")
try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"Static files mounted from: {static_dir}")
except RuntimeError as e:
    print(f"Static directory not found at {static_dir}, skipping mount: {e}")


# Pydantic models
class ScrapeRequest(BaseModel):
    url: str
    max_pages: int = 10
    max_depth: int = 2


class QueryRequest(BaseModel):
    question: str
    k: int = 6  # Increased from 4 to 6 for more context
    model: Optional[str] = None  # Optional LLM model to use


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    session_token: str
    message: str


class GateRequest(BaseModel):
    passphrase: str


class SearchRequest(BaseModel):
    query: str
    k: int = 5


class UpdateFolderRequest(BaseModel):
    folder: str


class CreateFolderRequest(BaseModel):
    folder_name: str


class CrawlRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 50
    delay: float = 1.0


class ScrapeMultipleRequest(BaseModel):
    urls: List[str]


class CreateDatabaseRequest(BaseModel):
    db_id: str
    name: str
    description: str = ""
    set_as_default: bool = False


class SwitchDatabaseRequest(BaseModel):
    db_id: str


class DuplicateDatabaseRequest(BaseModel):
    source_db_id: str
    new_db_id: str
    new_name: str
    description: str = ""


class PowerSearchRequest(BaseModel):
    question: str
    services: List[str]  # List of services to query: ["gemini", "chatgpt", "grok"]


class RateResponseRequest(BaseModel):
    message_id: str
    rating: str  # "acceptable" or "needs_improvement"
    content: str  # The actual response content
    feedback: Optional[str] = None  # Optional feedback text (required for needs_improvement)


class CreateUserRequest(BaseModel):
    username: str
    password: str
    user_type: str
    email: Optional[str] = None


class UpdateUserTypeRequest(BaseModel):
    user_type: str


class ChangePasswordRequest(BaseModel):
    new_password: str


class CreateTrainingSetRequest(BaseModel):
    name: str
    description: str = ""
    data: List[Dict]
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    data_format: str = "instruction"


class UpdateTrainingSetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class CloneTrainingSetRequest(BaseModel):
    new_name: str
    description: Optional[str] = None


class CreateFromQueryLogRequest(BaseModel):
    name: str
    description: str = ""
    filters: Optional[Dict] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CreateFromRatingsRequest(BaseModel):
    name: str
    description: str = ""
    rating_filter: str = "acceptable"
    username: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CreateTrainingRunRequest(BaseModel):
    run_name: str
    description: str = ""
    training_set_id: int
    test_set_id: Optional[int] = None
    base_model: str
    adapter_output_path: str
    config: Dict
    gpu_info: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict] = None


class UpdateTrainingRunRequest(BaseModel):
    status: Optional[str] = None
    final_train_loss: Optional[float] = None
    final_eval_loss: Optional[float] = None
    final_train_accuracy: Optional[float] = None
    final_eval_accuracy: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict] = None


class AddMetricRequest(BaseModel):
    step: int
    epoch: Optional[float] = None
    train_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    train_accuracy: Optional[float] = None
    eval_accuracy: Optional[float] = None
    learning_rate: Optional[float] = None
    metadata: Optional[Dict] = None


class AddLogRequest(BaseModel):
    log_level: str = "info"
    message: str
    metadata: Optional[Dict] = None


class AddCheckpointRequest(BaseModel):
    checkpoint_path: str
    step: int
    epoch: Optional[float] = None
    metrics: Optional[Dict] = None


# Helper functions for authentication
def generate_session_token(username: str, user_type: str, user_id: int = None) -> str:
    """Generate a session token for the given username, user type, and user ID."""
    return session_serializer.dumps({'username': username, 'user_type': user_type, 'id': user_id})


def verify_session_token(token: str) -> Optional[Dict]:
    """Verify a session token and return user info if valid."""
    try:
        # Max age is 24 hours (86400 seconds)
        data = session_serializer.loads(token, max_age=86400)
        username = data.get('username')
        user_type = data.get('user_type')
        user_id = data.get('id')
        if username and user_type:
            return {'username': username, 'user_type': user_type, 'id': user_id}
        return None
    except (BadSignature, SignatureExpired):
        return None


def generate_gate_token() -> str:
    """Generate a gate access token (valid indefinitely)."""
    import time
    return gate_serializer.dumps({'granted': True, 'timestamp': time.time()})


def verify_gate_token(token: str) -> bool:
    """Verify a gate token is valid (no expiration)."""
    try:
        # No expiration - token is valid indefinitely
        data = gate_serializer.loads(token)
        return data.get('granted') == True
    except (BadSignature, SignatureExpired):
        return False


async def verify_web_auth(authorization: Optional[str] = Header(None)):
    """Verify web authentication token and return user info."""
    if not WEB_AUTH_ENABLED:
        return {'username': 'demo', 'user_type': 'super'}

    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "")
        user_info = verify_session_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        return user_info
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_super_user(authorization: Optional[str] = Header(None)):
    """Verify user is authenticated and has super user privileges."""
    user_info = await verify_web_auth(authorization)
    if user_info['user_type'] != 'super':
        raise HTTPException(
            status_code=403,
            detail="Access denied. This operation requires super user privileges."
        )
    return user_info


# Routes
@app.get("/")
async def root():
    """Root endpoint - redirect to gate, login, or main interface."""
    from fastapi.responses import RedirectResponse
    if SITE_PASSPHRASE:
        # Site access gate enabled - redirect to gate page
        return RedirectResponse(url="/static/gate.html")
    elif WEB_AUTH_ENABLED:
        return RedirectResponse(url="/static/login.html")
    return RedirectResponse(url="/static/index.html")


@app.get("/version")
async def get_version():
    """Get application version information."""
    from version import get_version_info
    return get_version_info()


@app.post("/auth/login", response_model=LoginResponse)
async def login(login_req: LoginRequest, request: Request):
    """
    Authenticate user and return session token.
    Protected against brute force attacks with IP-based lockout.
    """
    # Get client IP address
    client_ip = get_remote_address(request)

    # Check if this IP is currently locked out
    if login_tracker.is_locked_out(client_ip):
        remaining = login_tracker.get_lockout_remaining(client_ip)
        minutes = remaining // 60
        seconds = remaining % 60
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Locked out for {minutes}m {seconds}s."
        )

    # Authenticate with user manager
    user_info = user_manager.authenticate(login_req.username, login_req.password)

    if user_info:
        # Successful login - clear any failed attempts
        login_tracker.record_successful_login(client_ip)
        token = generate_session_token(user_info['username'], user_info['user_type'], user_info.get('id'))
        return LoginResponse(
            success=True,
            session_token=token,
            message="Login successful"
        )
    else:
        # Failed login - record the attempt
        locked_out = login_tracker.record_failed_attempt(client_ip)

        if locked_out:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Locked out for 15 minutes."
            )

        # Tell user how many attempts remain
        remaining = login_tracker.get_attempts_remaining(client_ip)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid credentials. {remaining} attempt(s) remaining before 15-minute lockout."
        )


@app.get("/auth/verify")
async def verify_auth(user_info: Dict = Depends(verify_web_auth)):
    """Verify if the current session is valid and return user info."""
    return {
        "authenticated": True,
        "username": user_info['username'],
        "user_type": user_info['user_type']
    }


@app.post("/auth/logout")
async def logout(user_info: Dict = Depends(verify_web_auth)):
    """
    Logout endpoint - client should clear session token.
    This endpoint just validates the token is valid before logout.
    """
    return {"success": True, "message": "Logged out successfully"}


@app.post("/auth/verify-gate")
async def verify_gate(gate_req: GateRequest):
    """
    Verify the site access passphrase and return a gate token.
    This is the first layer of security before reaching the login page.
    """
    if not SITE_PASSPHRASE:
        # Gate not enabled
        raise HTTPException(status_code=404, detail="Gate verification not enabled")

    # Check passphrase
    if gate_req.passphrase == SITE_PASSPHRASE:
        # Generate gate token
        gate_token = generate_gate_token()

        # Create response with cookie
        response = JSONResponse(content={
            "success": True,
            "gate_token": gate_token,
            "message": "Access granted"
        })

        # Set gate token as httponly cookie for server-side verification
        response.set_cookie(
            key="gate_token",
            value=gate_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400 * 365  # 1 year
        )

        return response
    else:
        raise HTTPException(status_code=401, detail="Invalid passphrase")


@app.get("/auth/check-gate")
async def check_gate(x_gate_token: Optional[str] = Header(None)):
    """
    Check if a gate token is valid.
    Used to verify if user still has valid gate access.
    """
    if not SITE_PASSPHRASE:
        # Gate not enabled, allow access
        return {"valid": True}

    if not x_gate_token:
        raise HTTPException(status_code=401, detail="No gate token provided")

    if verify_gate_token(x_gate_token):
        return {"valid": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired gate token")


@app.post("/scrape")
@limiter.limit("2/hour")
async def scrape_website(scrape_req: ScrapeRequest, request: Request, authorized: bool = Depends(verify_admin_key)):
    """
    Scrape a website and ingest content into RAG system.
    Protected endpoint - requires admin API key and restricted in demo mode.
    """
    try:
        print(f"Starting scrape of {scrape_req.url}")

        # Initialize scraper
        scraper = WebScraper(max_pages=scrape_req.max_pages, delay=1.0)

        # Scrape website
        scraped_data = scraper.crawl(scrape_req.url, max_depth=scrape_req.max_depth)

        if not scraped_data:
            raise HTTPException(status_code=400, detail="No data was scraped from the website")

        # Ingest into RAG system
        rag_system.ingest_scraped_data(scraped_data)

        return {
            "success": True,
            "message": f"Successfully scraped and ingested {len(scraped_data)} pages",
            "pages_scraped": len(scraped_data),
            "urls": [item['url'] for item in scraped_data]
        }

    except Exception as e:
        print(f"Error in scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Upload and process a document into the RAG system.
    Supports: PDF, DOCX, PPTX, TXT, CSV, XLSX, XLS
    """
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # Save uploaded file
        file_path = upload_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Import document processor
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from document_processor import DocumentProcessor

        # Process the document (with OCR enabled for PDFs)
        processor = DocumentProcessor()
        processed_doc = processor.process_file(str(file_path), use_ocr=True)

        if not processed_doc or not processed_doc.get('content'):
            file_path.unlink()  # Delete file if processing failed
            raise HTTPException(status_code=400, detail="Could not extract text from document")

        # Ingest into RAG system
        results = rag_system.ingest_documents([{
            'content': processed_doc['content'],
            'metadata': {
                'source': file.filename,
                'type': processed_doc.get('type', 'uploaded_document')
            }
        }])

        # Clean up uploaded file
        file_path.unlink()

        result = results[0] if results else {}

        return {
            "success": True,
            "message": f"Successfully processed {file.filename}",
            "filename": file.filename,
            "doc_id": result.get('doc_id'),
            "chunks_created": result.get('chunks_created', 0),
            "file_type": processed_doc.get('type')
        }

    except Exception as e:
        print(f"Error in upload: {e}")
        if file_path.exists():
            file_path.unlink()  # Clean up on error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query_rag(query_req: QueryRequest, request: Request, user_info: Dict = Depends(verify_web_auth)):
    """
    Query the RAG system with a question.
    Rate limited to 20 queries per minute.
    Supports dynamic model selection.
    Requires authentication.
    """
    start_time = time.time()
    error_msg = None
    answer = ""
    sources = []

    try:
        # Determine which LLM model is being used
        llm_model = query_req.model if query_req.model else "llama3.1:8b"

        # If a specific model is requested, temporarily switch to it
        if query_req.model and query_req.model != rag_system.llm_provider:
            # Create temporary RAG system with requested model
            from langchain_ollama import OllamaLLM
            temp_llm = OllamaLLM(model=query_req.model, base_url="http://localhost:11434")

            # Temporarily swap the LLM
            original_llm = rag_system.llm
            rag_system.llm = temp_llm

            try:
                result = rag_system.query(query_req.question, k=query_req.k)
            finally:
                # Restore original LLM
                rag_system.llm = original_llm
        else:
            result = rag_system.query(query_req.question, k=query_req.k)

        answer = result['answer']
        sources = result['sources']

        # Calculate response time
        response_time = time.time() - start_time

        # Log the query with LLM model information, database ID, and user info
        query_logger.log_query(
            question=query_req.question,
            answer=answer,
            sources=sources,
            k=query_req.k,
            response_time=response_time,
            llm_model=llm_model,
            database_id=db_manager.active_database,
            username=user_info.get('username'),
            user_type=user_info.get('user_type'),
            user_id=user_info.get('id'),
            folder=getattr(query_req, 'folder', None)
        )

        return QueryResponse(
            answer=answer,
            sources=sources
        )

    except Exception as e:
        error_msg = str(e)
        response_time = time.time() - start_time
        llm_model = query_req.model if query_req.model else "llama3.1:8b"

        # Log the failed query with user info
        query_logger.log_query(
            question=query_req.question,
            answer="",
            sources=[],
            k=query_req.k,
            response_time=response_time,
            error=error_msg,
            llm_model=llm_model,
            database_id=db_manager.active_database,
            username=user_info.get('username'),
            user_type=user_info.get('user_type'),
            user_id=user_info.get('id'),
            folder=getattr(query_req, 'folder', None)
        )

        print(f"Error in query: {e}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/rate-response")
async def rate_response(
    rating_req: RateResponseRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Rate a response as acceptable or needs improvement.
    This is used by training users to provide feedback on AI responses.

    Args:
        rating_req: Rating details (message_id, rating, content)
        user_info: Authenticated user information

    Returns:
        Success status
    """
    try:
        # Only training users should be able to rate responses
        if user_info.get('user_type') != 'training':
            raise HTTPException(
                status_code=403,
                detail="Only training users can rate responses"
            )

        # Log the rating to a separate file for training data collection
        rating_log_dir = Path("logs/ratings")
        rating_log_dir.mkdir(parents=True, exist_ok=True)

        rating_log_file = rating_log_dir / f"ratings_{user_info['username']}.jsonl"

        import json
        from datetime import datetime

        rating_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "username": user_info['username'],
            "message_id": rating_req.message_id,
            "rating": rating_req.rating,
            "content": rating_req.content
        }

        # Add feedback if provided
        if rating_req.feedback:
            rating_entry["feedback"] = rating_req.feedback

        with open(rating_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rating_entry) + '\n')

        return {
            "success": True,
            "message": f"Rating '{rating_req.rating}' recorded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error recording rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """
    Get statistics about the RAG system and query logs for the active database.
    """
    try:
        # Get active database ID
        active_db_id = db_manager.active_database

        # Get RAG stats
        rag_stats = rag_system.get_stats()

        # Get database-specific query log stats
        log_stats = query_logger.get_stats(database_id=active_db_id)

        # Get webpage and document counts from database manager
        db_list = db_manager.list_databases()
        active_db_info = next((db for db in db_list if db['id'] == active_db_id), None)

        webpage_count = active_db_info['webpage_count'] if active_db_info else 0
        uploaded_count = active_db_info['uploaded_count'] if active_db_info else 0

        return {
            **rag_stats,
            "query_logs": log_stats,
            "webpage_count": webpage_count,
            "uploaded_count": uploaded_count,
            "database_id": active_db_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def get_available_models():
    """
    Get list of available LLM models from Ollama.
    """
    try:
        import subprocess
        import json

        # Run ollama list command
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception("Failed to get Ollama models")

        # Parse the output
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = []

        for line in lines:
            if line.strip():
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    models.append({
                        "name": model_name,
                        "display_name": model_name.replace(":", " ").title()
                    })

        return {"models": models}

    except Exception as e:
        print(f"Error getting models: {e}")
        # Return default models if ollama list fails
        return {
            "models": [
                {"name": "llama3.1:8b", "display_name": "Llama 3.1 8B"},
                {"name": "llama3.2:3b", "display_name": "Llama 3.2 3B"}
            ]
        }


@app.get("/logs/recent")
async def get_recent_logs(n: int = 10):
    """
    Get the N most recent query logs.

    Args:
        n: Number of recent queries to retrieve (default: 10)
    """
    try:
        return query_logger.get_recent_queries(n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/all")
async def get_all_logs():
    """
    Get all query logs.
    """
    try:
        return query_logger.get_all_queries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/export")
async def export_logs_csv():
    """
    Export query logs to CSV format.
    """
    try:
        from fastapi.responses import FileResponse
        csv_path = query_logger.export_to_csv()
        return FileResponse(
            path=csv_path,
            media_type="text/csv",
            filename="query_logs.csv"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents(user_info: Dict = Depends(verify_web_auth)):
    """
    List all documents in the RAG database.

    Returns:
        List of documents with their metadata
    """
    try:
        documents = rag_system.list_documents()
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Delete a document and all its chunks from the database.

    Args:
        doc_id: ID of the document to delete

    Returns:
        JSON response with deletion status
    """
    try:
        result = rag_system.delete_document(doc_id)

        if result['status'] == 'not_found':
            raise HTTPException(status_code=404, detail="Document not found")
        elif result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['error'])

        return {
            "message": "Document deleted successfully",
            "doc_id": doc_id,
            "chunks_deleted": result['chunks_deleted']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/{doc_id}/folder")
async def update_document_folder(
    doc_id: str,
    folder_request: UpdateFolderRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Update the folder assignment for a document.

    Args:
        doc_id: ID of the document to update
        folder_request: New folder name (empty string to remove folder)

    Returns:
        JSON response with update status
    """
    try:
        result = rag_system.update_document_folder(doc_id, folder_request.folder)

        if result['status'] == 'not_found':
            raise HTTPException(status_code=404, detail="Document not found")
        elif result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['error'])

        return {
            "message": "Document folder updated successfully",
            "doc_id": doc_id,
            "new_folder": result['new_folder'],
            "chunks_updated": result['chunks_updated']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/folders")
async def create_folder(
    folder_request: CreateFolderRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Create a new empty folder.

    Args:
        folder_request: Folder name

    Returns:
        JSON response with creation status
    """
    try:
        result = rag_system.create_folder(folder_request.folder_name)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "message": "Folder created successfully",
            "folder_name": result['folder_name']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/folders")
async def list_folders(user_info: Dict = Depends(verify_web_auth)):
    """
    List all folders (both empty and those with documents).

    Returns:
        JSON response with list of folder names
    """
    try:
        folders = rag_system.list_all_folders()
        return {"folders": folders}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/folders/{folder_name}")
async def delete_folder(
    folder_name: str,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Delete an empty folder.

    Args:
        folder_name: Name of the folder to delete

    Returns:
        JSON response with deletion status
    """
    try:
        result = rag_system.delete_folder(folder_name)

        if result['status'] == 'not_found':
            raise HTTPException(status_code=404, detail="Folder not found")
        elif result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "message": "Folder deleted successfully",
            "folder_name": result['folder_name']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_documents(
    search_request: SearchRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Search for relevant document chunks based on a query.

    Args:
        search_request: Search parameters (query and number of results)

    Returns:
        List of relevant document chunks with metadata
    """
    try:
        results = rag_system.search_documents(
            query=search_request.query,
            k=search_request.k
        )
        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crawl-website")
@limiter.limit("1/hour")
async def crawl_website(
    crawl_request: CrawlRequest,
    request: Request,
    user_info: Dict = Depends(verify_web_auth),
    authorized: bool = Depends(verify_admin_key)
):
    """
    Recursively crawl a website and ingest all pages into the RAG database.

    Args:
        crawl_request: Crawl configuration (URL, depth, max pages, delay, etc.)

    Returns:
        JSON response with crawling and ingestion status for all pages
    """
    try:
        print(f"Starting crawl of {crawl_request.url}")

        # Initialize scraper
        scraper = WebScraper(
            max_pages=crawl_request.max_pages,
            delay=crawl_request.delay
        )

        # Crawl website
        scraped_data = scraper.crawl(
            crawl_request.url,
            max_depth=crawl_request.max_depth
        )

        if not scraped_data:
            raise HTTPException(
                status_code=400,
                detail="No data was scraped from the website"
            )

        # Ingest into RAG system
        rag_system.ingest_scraped_data(scraped_data)

        return {
            "success": True,
            "message": f"Successfully crawled and ingested {len(scraped_data)} pages",
            "pages_crawled": len(scraped_data),
            "start_url": crawl_request.url,
            "max_depth": crawl_request.max_depth,
            "urls": [item['url'] for item in scraped_data]
        }

    except Exception as e:
        print(f"Error in crawl: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape-multiple-urls")
@limiter.limit("5/hour")
async def scrape_multiple_urls(
    scrape_request: ScrapeMultipleRequest,
    request: Request,
    user_info: Dict = Depends(verify_web_auth),
    authorized: bool = Depends(verify_admin_key)
):
    """
    Scrape multiple URLs and ingest their content into the RAG database.

    Args:
        scrape_request: List of URLs to scrape

    Returns:
        JSON response with scraping and ingestion status for each URL
    """
    results = []
    scraper = WebScraper(max_pages=len(scrape_request.urls), delay=1.0)

    for url in scrape_request.urls:
        try:
            # Scrape single URL
            scraped_data = scraper.crawl(url, max_depth=0)

            if scraped_data:
                # Ingest into RAG system
                rag_system.ingest_scraped_data(scraped_data)

                results.append({
                    "url": url,
                    "status": "success",
                    "pages_scraped": len(scraped_data)
                })
            else:
                results.append({
                    "url": url,
                    "status": "error",
                    "error": "Failed to scrape URL"
                })

        except Exception as e:
            results.append({
                "url": url,
                "status": "error",
                "error": str(e)
            })

    return {
        "message": f"Processed {len(scrape_request.urls)} URLs",
        "results": results
    }


@app.post("/clear")
async def clear_database(authorized: bool = Depends(verify_admin_key)):
    """
    Clear all data from the vector store.
    Protected endpoint - requires admin API key and disabled in demo mode.
    """
    try:
        rag_system.vector_store.clear_collection()
        return {
            "success": True,
            "message": "Vector store cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Database Management Endpoints
@app.get("/databases")
async def list_databases(user_info: Dict = Depends(verify_web_auth)):
    """
    List all available RAG databases.

    Returns:
        List of database configurations with stats
    """
    try:
        databases = db_manager.list_databases()
        return {"databases": databases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/databases")
async def create_database(
    db_request: CreateDatabaseRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Create a new RAG database.

    Args:
        db_request: Database configuration

    Returns:
        Creation status
    """
    try:
        result = db_manager.create_database(
            db_id=db_request.db_id,
            name=db_request.name,
            description=db_request.description,
            set_as_default=db_request.set_as_default
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Database '{result['name']}' created successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/databases/{db_id}")
async def delete_database_config(
    db_id: str,
    delete_files: bool = False,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Delete a database configuration.

    Args:
        db_id: Database ID to delete
        delete_files: Whether to delete actual database files

    Returns:
        Deletion status
    """
    try:
        result = db_manager.delete_database(db_id, delete_files=delete_files)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Database '{db_id}' deleted successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/databases/switch")
async def switch_database(
    switch_request: SwitchDatabaseRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Switch to a different RAG database.

    Args:
        switch_request: Database ID to switch to

    Returns:
        Switch status
    """
    global rag_system

    try:
        result = db_manager.set_active_database(switch_request.db_id)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        # Reinitialize RAG system with new database
        new_db_path = db_manager.get_database_path(switch_request.db_id)
        rag_system = RAGSystem(
            llm_provider="peft",
            model_name=PEFT_ADAPTER_PATH,
            vector_store=VectorStore(persist_directory=new_db_path)
        )

        return {
            "success": True,
            "message": f"Switched to database '{result['name']}'",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/databases/active")
async def get_active_database(user_info: Dict = Depends(verify_web_auth)):
    """
    Get information about the currently active database.

    Returns:
        Active database info
    """
    try:
        db_info = db_manager.get_active_database()
        stats = rag_system.get_stats()

        return {
            **db_info,
            "document_count": stats['vector_store']['count']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/databases/duplicate")
async def duplicate_database(
    duplicate_request: DuplicateDatabaseRequest,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Duplicate an existing database (copies all files).

    Args:
        duplicate_request: Source and new database details

    Returns:
        Duplication status
    """
    try:
        result = db_manager.duplicate_database(
            source_db_id=duplicate_request.source_db_id,
            new_db_id=duplicate_request.new_db_id,
            new_name=duplicate_request.new_name,
            description=duplicate_request.description
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Database duplicated successfully: {result['name']}",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/power-search/services")
async def get_available_power_search_services(user_info: Dict = Depends(verify_web_auth)):
    """
    Get list of available external AI services (those with API keys configured).

    Returns:
        List of service names that are available
    """
    try:
        services = power_search.get_available_services()
        return {
            "services": services,
            "all_services": ["gemini", "chatgpt", "grok"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/power-search")
@limiter.limit("10/minute")
async def power_search_query(
    search_req: PowerSearchRequest,
    request: Request,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Query multiple external AI services (Gemini, ChatGPT, Grok) in parallel.

    Args:
        search_req: Question and list of services to query

    Returns:
        Results from each selected AI service
    """
    try:
        start_time = time.time()

        # Validate services
        valid_services = ["gemini", "chatgpt", "grok"]
        for service in search_req.services:
            if service not in valid_services:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid service: {service}. Valid services are: {valid_services}"
                )

        if not search_req.services:
            raise HTTPException(
                status_code=400,
                detail="At least one service must be selected"
            )

        # Query the selected services
        results = await power_search.query_multiple(
            question=search_req.question,
            services=search_req.services
        )

        # Calculate total time
        total_time = time.time() - start_time
        results['total_time'] = round(total_time, 2)

        return results

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in power search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Management Endpoints (Super User Only)
@app.get("/users")
async def list_users(user_info: Dict = Depends(verify_super_user)):
    """
    List all users in the system.
    Requires super user privileges.

    Returns:
        List of all users with their info
    """
    try:
        users = user_manager.list_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/users")
async def create_user(
    user_req: CreateUserRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Create a new user.
    Requires super user privileges.

    Args:
        user_req: User creation details (username, password, user_type, email)

    Returns:
        Created user info
    """
    try:
        result = user_manager.create_user(
            username=user_req.username,
            password=user_req.password,
            user_type=user_req.user_type,
            email=user_req.email
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"User '{result['username']}' created successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{username}/type")
async def update_user_type(
    username: str,
    type_req: UpdateUserTypeRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Update a user's type/role.
    Requires super user privileges.

    Args:
        username: Username to update
        type_req: New user type

    Returns:
        Update status
    """
    try:
        result = user_manager.update_user_type(username, type_req.user_type)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"User '{username}' type updated to '{type_req.user_type}'",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{username}/password")
async def change_user_password(
    username: str,
    password_req: ChangePasswordRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Change a user's password.
    Requires super user privileges.

    Args:
        username: Username to update
        password_req: New password

    Returns:
        Update status
    """
    try:
        result = user_manager.change_password(username, password_req.new_password)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Password changed for user '{username}'",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/users/{username}")
async def deactivate_user(
    username: str,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Deactivate a user (soft delete).
    Requires super user privileges.

    Args:
        username: Username to deactivate

    Returns:
        Deactivation status
    """
    try:
        # Prevent deactivating yourself
        if username == user_info['username']:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate your own account"
            )

        result = user_manager.deactivate_user(username)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"User '{username}' deactivated successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Training Set Management Endpoints (Super User Only)
@app.get("/training/sets")
async def list_training_sets(
    status: Optional[str] = None,
    search: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: Optional[int] = None,
    user_info: Dict = Depends(verify_super_user)
):
    """
    List all training sets with optional filtering.
    Requires super user privileges.

    Args:
        status: Filter by status (active, archived, deprecated)
        search: Search in name and description
        created_by: Filter by creator
        limit: Limit number of results

    Returns:
        List of training sets
    """
    try:
        training_sets = training_manager.list_training_sets(
            status=status,
            search=search,
            created_by=created_by,
            limit=limit
        )
        return {"training_sets": training_sets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/sets")
async def create_training_set(
    ts_req: CreateTrainingSetRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Create a new training set.
    Requires super user privileges.

    Args:
        ts_req: Training set creation details

    Returns:
        Created training set info
    """
    try:
        result = training_manager.create_training_set(
            name=ts_req.name,
            data=ts_req.data,
            created_by=user_info['username'],
            description=ts_req.description,
            categories=ts_req.categories,
            tags=ts_req.tags,
            data_format=ts_req.data_format
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training set '{result['name']}' created successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/sets/{ts_id}")
async def get_training_set(
    ts_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get training set details by ID.
    Requires super user privileges.

    Args:
        ts_id: Training set ID

    Returns:
        Training set details
    """
    try:
        training_set = training_manager.get_training_set(ts_id)
        if not training_set:
            raise HTTPException(status_code=404, detail="Training set not found")

        return training_set
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/sets/{ts_id}/data")
async def get_training_set_data(
    ts_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get the actual training data from a training set.
    Requires super user privileges.

    Args:
        ts_id: Training set ID

    Returns:
        List of training examples
    """
    try:
        data = training_manager.get_training_data(ts_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Training set not found or data file missing")

        return {"data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/training/sets/{ts_id}")
async def update_training_set(
    ts_id: int,
    ts_req: UpdateTrainingSetRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Update training set metadata.
    Requires super user privileges.

    Args:
        ts_id: Training set ID
        ts_req: Update details

    Returns:
        Update status
    """
    try:
        result = training_manager.update_training_set(
            training_set_id=ts_id,
            modified_by=user_info['username'],
            name=ts_req.name,
            description=ts_req.description,
            categories=ts_req.categories,
            tags=ts_req.tags,
            status=ts_req.status
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": "Training set updated successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/training/sets/{ts_id}")
async def delete_training_set(
    ts_id: int,
    delete_file: bool = True,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Delete a training set.
    Requires super user privileges.

    Args:
        ts_id: Training set ID
        delete_file: Whether to delete the actual file (default: True)

    Returns:
        Deletion status
    """
    try:
        result = training_manager.delete_training_set(ts_id, delete_file=delete_file)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training set '{result['name']}' deleted successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/sets/{ts_id}/clone")
async def clone_training_set(
    ts_id: int,
    clone_req: CloneTrainingSetRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Clone an existing training set.
    Requires super user privileges.

    Args:
        ts_id: Training set ID to clone
        clone_req: Clone details (new name, description)

    Returns:
        Cloned training set info
    """
    try:
        result = training_manager.clone_training_set(
            training_set_id=ts_id,
            new_name=clone_req.new_name,
            created_by=user_info['username'],
            description=clone_req.description
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training set cloned as '{result['name']}'",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/sets/from-query-log")
async def create_training_set_from_query_log(
    req: CreateFromQueryLogRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Create a training set from master query log with optional filtering.
    Requires super user privileges.

    Args:
        req: Request details including name, filters, and metadata

    Returns:
        Created training set info

    Filter options:
        - success_only: Only include successful queries (default: True)
        - user_type: Filter by user type (super, training, standard)
        - username: Filter by specific username
        - database_id: Filter by database ID
        - max_examples: Limit number of examples to include
    """
    try:
        result = training_manager.create_from_query_log(
            name=req.name,
            created_by=user_info['username'],
            filters=req.filters or {},
            description=req.description,
            categories=req.categories,
            tags=req.tags
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training set '{result['name']}' created from query log with {result['example_count']} examples",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/sets/from-ratings")
async def create_training_set_from_ratings(
    req: CreateFromRatingsRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Create a training set from training user ratings.
    Requires super user privileges.

    Args:
        req: Request details including name, rating filter, and metadata

    Returns:
        Created training set info

    Rating filter options:
        - acceptable: Only include responses rated as acceptable
        - needs_improvement: Only include responses rated as needs improvement (includes feedback)
        - all: Include all ratings
    """
    try:
        result = training_manager.create_from_ratings(
            name=req.name,
            created_by=user_info['username'],
            rating_filter=req.rating_filter,
            username=req.username,
            description=req.description,
            categories=req.categories,
            tags=req.tags
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training set '{result['name']}' created from ratings with {result['example_count']} examples",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Training Run Tracker Endpoints (Super User Only)
@app.get("/training/runs")
async def list_training_runs(
    status: Optional[str] = None,
    search: Optional[str] = None,
    created_by: Optional[str] = None,
    training_set_id: Optional[int] = None,
    limit: Optional[int] = None,
    user_info: Dict = Depends(verify_super_user)
):
    """
    List all training runs with optional filtering.
    Requires super user privileges.

    Args:
        status: Filter by status (running, completed, failed, stopped)
        search: Search in name and description
        created_by: Filter by creator username
        training_set_id: Filter by training set ID
        limit: Limit number of results

    Returns:
        List of training runs
    """
    try:
        runs = training_run_tracker.list_training_runs(
            status=status,
            search=search,
            created_by=created_by,
            training_set_id=training_set_id,
            limit=limit
        )
        return {"training_runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/runs")
async def create_training_run(
    run_req: CreateTrainingRunRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Create a new training run.
    Requires super user privileges.

    Args:
        run_req: Training run creation details

    Returns:
        Created training run info
    """
    try:
        result = training_run_tracker.create_training_run(
            run_name=run_req.run_name,
            training_set_id=run_req.training_set_id,
            base_model=run_req.base_model,
            adapter_output_path=run_req.adapter_output_path,
            config=run_req.config,
            created_by=user_info['username'],
            description=run_req.description,
            test_set_id=run_req.test_set_id,
            gpu_info=run_req.gpu_info,
            notes=run_req.notes,
            metadata=run_req.metadata
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training run '{result['run_name']}' created successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/runs/{run_id}")
async def get_training_run(
    run_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get training run details by ID.
    Requires super user privileges.

    Args:
        run_id: Training run ID

    Returns:
        Training run details
    """
    try:
        run = training_run_tracker.get_training_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")

        return run
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/training/runs/{run_id}")
async def update_training_run(
    run_id: int,
    update_req: UpdateTrainingRunRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Update training run status and final results.
    Requires super user privileges.

    Args:
        run_id: Training run ID
        update_req: Update details

    Returns:
        Update status
    """
    try:
        result = training_run_tracker.update_training_run_status(
            run_id=run_id,
            status=update_req.status,
            final_train_loss=update_req.final_train_loss,
            final_eval_loss=update_req.final_eval_loss,
            final_train_accuracy=update_req.final_train_accuracy,
            final_eval_accuracy=update_req.final_eval_accuracy,
            notes=update_req.notes,
            metadata=update_req.metadata
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": "Training run updated successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/training/runs/{run_id}")
async def delete_training_run(
    run_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Delete a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID

    Returns:
        Deletion status
    """
    try:
        result = training_run_tracker.delete_training_run(run_id)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": f"Training run '{result['run_name']}' deleted successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/runs/{run_id}/metrics")
async def get_training_run_metrics(
    run_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get all metrics for a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID

    Returns:
        List of metric points for charting
    """
    try:
        metrics = training_run_tracker.get_metrics(run_id)
        return {"metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/runs/{run_id}/metrics")
async def add_training_run_metric(
    run_id: int,
    metric_req: AddMetricRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Add a metric point to a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID
        metric_req: Metric data

    Returns:
        Created metric info
    """
    try:
        result = training_run_tracker.add_metric(
            run_id=run_id,
            step=metric_req.step,
            epoch=metric_req.epoch,
            train_loss=metric_req.train_loss,
            eval_loss=metric_req.eval_loss,
            train_accuracy=metric_req.train_accuracy,
            eval_accuracy=metric_req.eval_accuracy,
            learning_rate=metric_req.learning_rate,
            metadata=metric_req.metadata
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": "Metric added successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/runs/{run_id}/logs")
async def get_training_run_logs(
    run_id: int,
    log_level: Optional[str] = None,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get all logs for a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID
        log_level: Filter by log level (info, warning, error)

    Returns:
        List of log entries
    """
    try:
        logs = training_run_tracker.get_logs(run_id, log_level=log_level)
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/runs/{run_id}/logs")
async def add_training_run_log(
    run_id: int,
    log_req: AddLogRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Add a log entry to a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID
        log_req: Log entry data

    Returns:
        Created log entry info
    """
    try:
        result = training_run_tracker.add_log(
            run_id=run_id,
            log_level=log_req.log_level,
            message=log_req.message,
            metadata=log_req.metadata
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": "Log entry added successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/runs/{run_id}/checkpoints")
async def get_training_run_checkpoints(
    run_id: int,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get all checkpoints for a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID

    Returns:
        List of checkpoint entries
    """
    try:
        checkpoints = training_run_tracker.get_checkpoints(run_id)
        return {"checkpoints": checkpoints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/runs/{run_id}/checkpoints")
async def add_training_run_checkpoint(
    run_id: int,
    checkpoint_req: AddCheckpointRequest,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Add a checkpoint to a training run.
    Requires super user privileges.

    Args:
        run_id: Training run ID
        checkpoint_req: Checkpoint data

    Returns:
        Created checkpoint info
    """
    try:
        # Extract metrics from request if provided
        train_loss = None
        eval_loss = None
        train_accuracy = None
        eval_accuracy = None
        if checkpoint_req.metrics:
            train_loss = checkpoint_req.metrics.get('train_loss')
            eval_loss = checkpoint_req.metrics.get('eval_loss')
            train_accuracy = checkpoint_req.metrics.get('train_accuracy')
            eval_accuracy = checkpoint_req.metrics.get('eval_accuracy')

        result = training_run_tracker.add_checkpoint(
            run_id=run_id,
            checkpoint_step=checkpoint_req.step,
            checkpoint_path=checkpoint_req.checkpoint_path,
            train_loss=train_loss,
            eval_loss=eval_loss,
            train_accuracy=train_accuracy,
            eval_accuracy=eval_accuracy
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "message": "Checkpoint added successfully",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/runs/compare")
async def compare_training_runs(
    ids: str,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Compare multiple training runs side by side.
    Requires super user privileges.

    Args:
        ids: Comma-separated list of training run IDs (e.g., "1,2,3")

    Returns:
        Comparison data for all runs
    """
    try:
        # Parse comma-separated IDs
        run_ids = [int(id.strip()) for id in ids.split(",")]

        if len(run_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 training runs are required for comparison"
            )

        result = training_run_tracker.compare_runs(run_ids)

        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['error'])

        return result
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid IDs format. Use comma-separated integers (e.g., '1,2,3')"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Documentation Endpoints
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules', '.pytest_cache'}

@app.get("/docs/list")
async def list_docs(user_info: Dict = Depends(verify_web_auth)):
    """List all markdown files in the project."""
    try:
        md_files = []
        for path in sorted(Path(PROJECT_ROOT).rglob("*.md")):
            # Skip excluded directories
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            rel_path = str(path.relative_to(PROJECT_ROOT))
            md_files.append({
                "path": rel_path,
                "name": path.name,
                "dir": str(path.parent.relative_to(PROJECT_ROOT)) if path.parent != Path(PROJECT_ROOT) else ""
            })
        return {"files": md_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs/content")
async def get_doc_content(path: str, user_info: Dict = Depends(verify_web_auth)):
    """Get the content of a markdown file by relative path."""
    try:
        # Resolve and validate path is within project root
        full_path = (Path(PROJECT_ROOT) / path).resolve()
        if not str(full_path).startswith(str(Path(PROJECT_ROOT).resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        if not full_path.exists() or not full_path.suffix == ".md":
            raise HTTPException(status_code=404, detail="File not found")
        if any(part in EXCLUDE_DIRS for part in full_path.parts):
            raise HTTPException(status_code=403, detail="Access denied")
        return {"path": path, "content": full_path.read_text(encoding="utf-8")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Protected static HTML routes - must have valid gate token to access
@app.get("/static/login.html")
async def serve_login_page(request: Request):
    """Serve login page only if user has valid gate token."""
    from fastapi.responses import FileResponse, RedirectResponse

    if SITE_PASSPHRASE:
        # Check for gate token in cookie
        gate_token = request.cookies.get("gate_token")

        if not gate_token or not verify_gate_token(gate_token):
            # No valid gate token - redirect to gate page
            return RedirectResponse(url="/static/gate.html", status_code=303)

    # Gate token valid or gate not enabled - serve login page
    return FileResponse(os.path.join(static_dir, "login.html"))


@app.get("/static/index.html")
async def serve_index_page(request: Request):
    """Serve index page only if user has valid gate token."""
    from fastapi.responses import FileResponse, RedirectResponse

    if SITE_PASSPHRASE:
        # Check for gate token in cookie
        gate_token = request.cookies.get("gate_token")

        if not gate_token or not verify_gate_token(gate_token):
            # No valid gate token - redirect to gate page
            return RedirectResponse(url="/static/gate.html", status_code=303)

    # Gate token valid or gate not enabled - serve index page
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/static/docs.html")
async def serve_docs_page(request: Request):
    """Serve docs page only if user has valid gate token."""
    from fastapi.responses import FileResponse, RedirectResponse

    if SITE_PASSPHRASE:
        # Check for gate token in cookie
        gate_token = request.cookies.get("gate_token")

        if not gate_token or not verify_gate_token(gate_token):
            # No valid gate token - redirect to gate page
            return RedirectResponse(url="/static/gate.html", status_code=303)

    # Gate token valid or gate not enabled - serve docs page
    return FileResponse(os.path.join(static_dir, "docs.html"))


@app.get("/static/training_sets.html")
async def serve_training_sets_page(request: Request):
    """Serve training sets page only if user has valid gate token."""
    from fastapi.responses import FileResponse, RedirectResponse

    if SITE_PASSPHRASE:
        # Check for gate token in cookie
        gate_token = request.cookies.get("gate_token")

        if not gate_token or not verify_gate_token(gate_token):
            # No valid gate token - redirect to gate page
            return RedirectResponse(url="/static/gate.html", status_code=303)

    # Gate token valid or gate not enabled - serve training sets page
    return FileResponse(os.path.join(static_dir, "training_sets.html"))


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("APP_PORT", 8005))
    uvicorn.run(app, host="0.0.0.0", port=port)
