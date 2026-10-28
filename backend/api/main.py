"""
FastAPI backend for the RAG chat system.
"""

from fastapi import FastAPI, HTTPException, Header, Request, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
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
from api.secrets_manager import ensure_secrets as _ensure_secrets, get_secret_key as _get_secret_key
_ensure_secrets()  # TB-US-050: boot-time read/generate before anything else needs it

from api.schema_migrations import apply_versioning_schema as _apply_versioning_schema
from api.schema_migrations import migrate_appsettings_prompt_and_routes as _migrate_appsettings_prompt_and_routes
_schema_result = _apply_versioning_schema()  # TB-US-051: idempotent versioning-tables migration
print(f"[schema] {_schema_result}")
_appsettings_migration = _migrate_appsettings_prompt_and_routes()  # TB-US-055 R8/R9
print(f"[schema] {_appsettings_migration}")

from api.first_run_seeder import seed_math_example as _seed_math_example  # TB-US-057 Phase A
_seed_result = _seed_math_example()
print(f"[seeder] {_seed_result}")

# TB-US-065: auto-reap child subprocesses (training runs). Without this,
# killed / completed train.py children become zombies waiting for the
# parent uvicorn to call wait(). Setting SIGCHLD → SIG_IGN tells the
# kernel to auto-reap. Harmless side-effect: Popen.poll() may return
# None for a completed child; we rely on the DB status column, not
# Popen state, so this is fine.
import signal as _signal
try:
    _signal.signal(_signal.SIGCHLD, _signal.SIG_IGN)
except (AttributeError, OSError):
    pass  # non-POSIX platforms (unlikely for TB server)

# TB-US-065 R9: startup reconciliation — flip stale 'running' rows
# whose subprocess died when TB was restarted. Must run before any
# launch endpoint accepts requests.
from api.training_run_tracker import TrainingRunTracker as _TRT_startup
_flipped_runs = _TRT_startup().startup_reconcile()
print(f"[training-runs] startup_reconcile flipped {len(_flipped_runs)} stale run(s): {_flipped_runs}")

from api.user_manager import UserManager
from api.training_manager import TrainingSetManager
from api.training_set_version_manager import TrainingSetVersionManager  # TB-US-052
from api.rag_version_manager import RAGVersionManager  # TB-US-053
from api.adapter_version_manager import AdapterVersionManager  # TB-US-054
from api.prompt_version_manager import PromptVersionManager  # TB-US-055
from api.route_version_manager import RouteVersionManager  # TB-US-055
from api.harness_version_manager import HarnessVersionManager  # TB-US-056
from api.experiment_manager import ExperimentManager, ExperimentError  # TB-US-056
from api import harness_runner as _harness_runner  # TB-US-056
from api.agent_manager import AgentManager, AgentError  # TB-US-048
from api.api_key_manager import ApiKeyManager, ApiKeyError  # TB-US-063
from api.versioned_component import VersionedComponentError  # TB-US-052
from api.training_run_tracker import TrainingRunTracker
from api.app_settings import AppSettings
from api.spreadsheet_calculator import SpreadsheetCalculator
from api.session_tracker import SessionTracker
import time
import shutil
import json  # TB-US-019: session storage + export
from datetime import datetime  # TB-US-019: training session timestamps
from pathlib import Path

# Configuration
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Authentication configuration
WEB_AUTH_ENABLED = os.getenv("WEB_AUTH_ENABLED", "true").lower() == "true"
# TB-US-050: SECRET_KEY now comes from secrets_manager (env wins over
# auto-generated .secrets file). The hardcoded fallback is gone — fresh
# installs get a strong random key automatically.
SECRET_KEY = _get_secret_key()

# RAG generation backend selection. The RAG system supports several
# providers (peft, ollama, openai, huggingface). Choose at runtime via
# env var; default is peft.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "peft").lower()
# Model identifier passed to the chosen provider. If unset, the provider
# falls back to its own default (e.g. PEFT_ADAPTER_PATH env for peft,
# OLLAMA_MODEL env for ollama). Set this to override per-deployment.
LLM_MODEL = os.getenv("LLM_MODEL") or None

# TB-US-035: Active PEFT adapter reporter (direct port from stalite3).
# These module-level globals back the GET /active-adapter endpoint. TB
# does not hardcode a default adapter the way stalite3 does; operators
# set TB_ACTIVE_ADAPTER in /etc/default/trainingbench if an active-
# adapter concept is wanted for their deployment. If unset, the
# endpoint returns {"adapter": null, "adapter_path": null}.
ACTIVE_ADAPTER = os.getenv("TB_ACTIVE_ADAPTER") or None
ACTIVE_ADAPTER_PATH = (
    f"training/adapters/{ACTIVE_ADAPTER}" if ACTIVE_ADAPTER else None
)

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


# Prevent browsers from caching served HTML pages. Without this, an
# updated HTML file on disk can be masked by the browser's cached
# copy for hours after the fix is deployed. Applies to any response
# whose path ends in .html — covers the StaticFiles mount at /static
# as well as any custom HTML routes.
@app.middleware("http")
async def add_no_cache_headers_for_html(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response

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

# TB-US-037: Optional spreadsheet calculator wired as the RAGSystem's
# `calculator` hook. If TB_SPREADSHEET_PATH env var is set and loads
# successfully, calculation questions get a deterministic answer from
# the spreadsheet (STEP 1) before falling through to RAG (STEP 2),
# matching stalite3's integration pattern. Fail-soft: load errors
# degrade to RAG-only mode without crashing the service.
TB_SPREADSHEET_PATH = os.getenv("TB_SPREADSHEET_PATH") or None
spreadsheet_calculator = None
if TB_SPREADSHEET_PATH:
    try:
        spreadsheet_calculator = SpreadsheetCalculator(TB_SPREADSHEET_PATH)
        print(f"Spreadsheet calculator loaded from: {TB_SPREADSHEET_PATH}")
    except Exception as e:
        print(f"Warning: SpreadsheetCalculator failed to load from {TB_SPREADSHEET_PATH}: {e}")
        spreadsheet_calculator = None

rag_system = RAGSystem(
    llm_provider=LLM_PROVIDER,
    model_name=LLM_MODEL,
    vector_store=VectorStore(persist_directory=active_db_path),
    calculator=spreadsheet_calculator.calculate if spreadsheet_calculator else None,
)

# Initialize query logger
query_logger = QueryLogger(log_dir="logs")

# Initialize login tracker (5 attempts, 15 minute lockout)
login_tracker = LoginTracker(max_attempts=5, lockout_duration=900)

# Initialize user manager
user_manager = UserManager()

# TB-US-034: Initialize session tracker. sessions.db is auto-created
# at /home/jeversole/trainingbench/sessions.db (relative to systemd
# WorkingDirectory). SessionTracker._init_database creates the
# sessions table on first instantiation; no manual migration required.
session_tracker = SessionTracker()

# Initialize power search service
power_search = PowerSearchService()

# Initialize training set manager
training_manager = TrainingSetManager()
training_set_version_manager = TrainingSetVersionManager()  # TB-US-052
rag_version_manager = RAGVersionManager()  # TB-US-053
adapter_version_manager = AdapterVersionManager()  # TB-US-054
prompt_version_manager = PromptVersionManager()  # TB-US-055
route_version_manager = RouteVersionManager()  # TB-US-055
harness_version_manager = HarnessVersionManager()  # TB-US-056
experiment_manager = ExperimentManager()  # TB-US-056
agent_manager = AgentManager()  # TB-US-048
api_key_manager = ApiKeyManager()  # TB-US-063

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
    must_change_password: bool = False


class SelfChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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


class ModeUpdateRequest(BaseModel):
    demo_mode: bool


# TB-US-033: Pydantic models for /settings/rag-prompt and /settings/query-routes
class RagPromptRequest(BaseModel):
    prompt: str


class QueryRoutesRequest(BaseModel):
    routes: List[Dict]


# TB-US-017: user management v2 request models
class SetActiveRequest(BaseModel):
    active: bool


class UpdateEmailRequest(BaseModel):
    email: Optional[str] = None


class BulkActionRequest(BaseModel):
    action: str  # 'deactivate' | 'activate' | 'delete'
    usernames: List[str]


# TB-US-019: training session workflow (direct port from stalite3)
class TrainingSessionRequest(BaseModel):
    session_name: str
    session_state: str  # 'not_started' | 'active' | 'completed'
    record_count: int = 0


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


# TB-US-052: training-set versioning request bodies
class CreateTrainingSetVersionRequest(BaseModel):
    agent_id: int
    samples: List[Dict]
    parent_version_id: Optional[int] = None


# TB-US-053: RAG versioning request bodies
class CreateRAGVersionRequest(BaseModel):
    agent_id: int
    embedding_model: str = "all-MiniLM-L6-v2"
    parent_version_id: Optional[int] = None


class IngestRAGDocsRequest(BaseModel):
    docs: List[Dict]


# TB-US-054: adapter versioning request body
class RegisterAdapterRequest(BaseModel):
    agent_id: int
    agent_slug: str
    source_dir: str
    base_model: str
    training_set_version_id: Optional[int] = None
    training_run_metadata: Optional[Dict] = None
    parent_version_id: Optional[int] = None


# TB-US-055: prompt + routes versioning request bodies
class CreatePromptVersionRequest(BaseModel):
    agent_id: int
    content: str
    parent_version_id: Optional[int] = None


class CreateRouteVersionRequest(BaseModel):
    agent_id: int
    routes: List[Dict]
    parent_version_id: Optional[int] = None


# TB-US-056: harness + experiment request bodies
class CreateHarnessVersionRequest(BaseModel):
    agent_id: int
    definition: Dict         # {"module": "harnesses.math_qa_v1", "config": {...}}
    parent_version_id: Optional[int] = None


class CreateExperimentRequest(BaseModel):
    agent_id: int
    label: str
    harness_version_id: int
    system_prompt_version_id: Optional[int] = None
    rag_version_id: Optional[int] = None
    llm_identifier: Optional[str] = None
    adapter_version_id: Optional[int] = None
    parent_experiment_id: Optional[int] = None


# TB-US-048: agent management request bodies
class CreateAgentRequest(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None


# TB-US-065: launch training-run request body
class LaunchTrainingRunRequest(BaseModel):
    run_name: str
    description: Optional[str] = None
    training_set_version_id: int
    base_model: str = "meta-llama/Meta-Llama-3.1-8B"
    hyperparameters: Dict = {}
    agent_id: Optional[int] = None
    notes: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    new_name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None  # 'active' or 'retired' for direct state flip


# TB-US-063: API-key create request
class CreateApiKeyRequest(BaseModel):
    label: str


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


async def verify_training_or_super(authorization: Optional[str] = Header(None)):
    """Verify user is authenticated as either a super or training user."""
    user_info = await verify_web_auth(authorization)
    if user_info['user_type'] not in ('super', 'training'):
        raise HTTPException(
            status_code=403,
            detail="Access denied. This operation requires super or training user privileges."
        )
    return user_info


def _authorize_training_set(user_info: Dict, ts_id: int) -> Dict:
    """Return the training set if the caller may act on it, else 404.

    Super users act on any set; training users act only on sets they
    authored. 404 (not 403) on cross-user access to avoid leaking IDs.
    """
    ts = training_manager.get_training_set(ts_id)
    if not ts:
        raise HTTPException(status_code=404, detail="Training set not found")
    if user_info['user_type'] == 'super':
        return ts
    if user_info['user_type'] == 'training' and ts.get('created_by') == user_info['username']:
        return ts
    raise HTTPException(status_code=404, detail="Training set not found")


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


@app.get("/settings/mode")
async def get_settings_mode(user_info: dict = Depends(verify_web_auth)):
    """Return the current demo_mode flag for the UI mode pill."""
    return {"demo_mode": AppSettings.demo_mode()}


@app.put("/settings/mode")
async def update_settings_mode(
    req: ModeUpdateRequest,
    user_info: dict = Depends(verify_super_user),
):
    """Toggle demo_mode. Super-user only; AppSettings appends an audit entry."""
    return AppSettings.set_demo_mode(req.demo_mode, user_info["username"])


# TB-US-033: /settings/rag-prompt and /settings/query-routes endpoints
# (direct port from stalite3). Reads are open to any authed user; writes
# require super user.

@app.get("/settings/rag-prompt")
async def get_rag_prompt(user_info: Dict = Depends(verify_web_auth)):
    """Return the current RAG prompt template, built-in default, and save metadata."""
    from api.app_settings import DEFAULT_RAG_PROMPT
    meta = AppSettings.rag_prompt_meta()
    return {
        "prompt": AppSettings.rag_prompt(),
        "default": DEFAULT_RAG_PROMPT,
        "saved_at": meta["saved_at"],
        "saved_by": meta["saved_by"],
    }


@app.put("/settings/rag-prompt")
async def set_rag_prompt(req: RagPromptRequest, user_info: Dict = Depends(verify_super_user)):
    """Set the RAG prompt template. Super-user only. Writes to the audit log.

    Validates presence of both `{context}` and `{question}` placeholders;
    without them the template would fail to format at query time.
    """
    if "{context}" not in req.prompt or "{question}" not in req.prompt:
        raise HTTPException(
            status_code=400,
            detail="Prompt template must contain both {context} and {question} placeholders.",
        )
    return AppSettings.set_rag_prompt(req.prompt, user_info["username"])


@app.get("/settings/query-routes")
async def get_query_routes(user_info: Dict = Depends(verify_web_auth)):
    """Return the current query routes, built-in defaults, and save metadata."""
    from api.app_settings import DEFAULT_QUERY_ROUTES
    meta = AppSettings.query_routes_meta()
    return {
        "routes": AppSettings.query_routes(),
        "defaults": list(DEFAULT_QUERY_ROUTES),
        "saved_at": meta["saved_at"],
        "saved_by": meta["saved_by"],
    }


@app.put("/settings/query-routes")
async def set_query_routes(req: QueryRoutesRequest, user_info: Dict = Depends(verify_super_user)):
    """Set the query routes list. Super-user only. Writes to the audit log.

    Validates each route has the required keys: name (str), patterns (list),
    augmentation (str), augmentation_position (str), enabled (bool).
    """
    required_keys = {"name", "patterns", "augmentation", "augmentation_position", "enabled"}
    for i, route in enumerate(req.routes):
        if not isinstance(route, dict):
            raise HTTPException(status_code=400, detail=f"Route #{i} must be an object.")
        missing = required_keys - set(route.keys())
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Route #{i} ({route.get('name', '<unnamed>')}) missing keys: {sorted(missing)}",
            )
        if not isinstance(route.get("patterns"), list):
            raise HTTPException(
                status_code=400,
                detail=f"Route #{i} 'patterns' must be a list.",
            )
    return AppSettings.set_query_routes(req.routes, user_info["username"])


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

        # TB-US-034: record session. Best-effort — a session_tracker
        # failure must not block the user from logging in.
        try:
            user_agent = request.headers.get('user-agent', '')
            session_tracker.create_session(
                user_id=user_info.get('id'),
                username=user_info['username'],
                user_type=user_info['user_type'],
                session_token=token,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as e:
            print(f"Warning: session_tracker.create_session failed: {e}")

        return LoginResponse(
            success=True,
            session_token=token,
            message="Login successful",
            must_change_password=bool(user_info.get("must_change_password", False)),
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
        "user_type": user_info['user_type'],
        # TB-US-049: surface the flag so the UI can gate index.html
        "must_change_password": user_manager.must_change_password(user_info['username']),
        # TB-US-059: surface the welcome-banner dismissal flag.
        "welcome_banner_dismissed": user_manager.welcome_banner_dismissed(user_info['username']),
    }


@app.post("/auth/dismiss-welcome")
async def dismiss_welcome(user_info: Dict = Depends(verify_web_auth)):
    """TB-US-059: mark the current user's welcome banner as dismissed."""
    result = user_manager.set_welcome_banner_dismissed(user_info['username'], True)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "dismiss failed"))
    return {"success": True, "dismissed": True}


@app.post("/auth/reset-welcome")
async def reset_welcome(user_info: Dict = Depends(verify_web_auth)):
    """TB-US-059: clear the dismissal flag so the welcome banner shows again."""
    result = user_manager.set_welcome_banner_dismissed(user_info['username'], False)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "reset failed"))
    return {"success": True, "dismissed": False}


@app.post("/auth/change-password")
async def self_change_password(
    req: SelfChangePasswordRequest,
    user_info: Dict = Depends(verify_web_auth),
):
    """TB-US-049: let an authenticated user change their own password.

    Verifies the current password; writes the new hash; clears the
    `must_change_password` flag; deletes `logs/first-run-admin.txt` if
    present. Any authenticated user can call this against their own
    account — super-only admin password resets still go through
    PUT /users/{username}/password.
    """
    username = user_info['username']
    result = user_manager.self_change_password(
        username=username,
        current_password=req.current_password,
        new_password=req.new_password,
    )
    if result['status'] != 'success':
        user_manager.append_audit(
            actor=username, action='change_password',
            target=username, details={"error": result['error']}, success=False,
        )
        raise HTTPException(status_code=400, detail=result['error'])

    user_manager.append_audit(
        actor=username, action='change_password',
        target=username, details={}, success=True,
    )
    return {"success": True, "message": "Password changed"}


@app.post("/auth/logout")
async def logout(
    user_info: Dict = Depends(verify_web_auth),
    authorization: Optional[str] = Header(None),
):
    """
    Logout endpoint - client should clear session token.
    This endpoint validates the token is valid before logout and
    marks the session closed in session_tracker (TB-US-034).
    """
    # TB-US-034: close the session record. Best-effort.
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            session_tracker.close_session(token, close_type="closed")
        except Exception as e:
            print(f"Warning: session_tracker.close_session failed: {e}")
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
async def get_stats(database_id: Optional[str] = None):
    """
    Get statistics about the RAG system and query logs for a database.
    If database_id is omitted, uses the active database. If a non-active
    database_id is supplied, chunk-level metrics come from the target
    database's ChromaDB, not the active RAG system.
    """
    try:
        target_db_id = database_id or db_manager.active_database

        db_list = db_manager.list_databases()
        target_db_info = next((db for db in db_list if db['id'] == target_db_id), None)
        if not target_db_info:
            raise HTTPException(status_code=404, detail=f"Database '{target_db_id}' not found")

        log_stats = query_logger.get_stats(database_id=target_db_id)
        webpage_count = target_db_info['webpage_count']
        uploaded_count = target_db_info['uploaded_count']

        if target_db_id == db_manager.active_database:
            rag_stats = rag_system.get_stats()
        else:
            # For non-active DBs, list_databases() already read the chunk
            # count. Wrap into the same shape the frontend expects so the
            # renderer stays uniform across active/non-active.
            rag_stats = {
                "vector_store": {"count": target_db_info['chunk_count']}
            }

        return {
            **rag_stats,
            "query_logs": log_stats,
            "webpage_count": webpage_count,
            "uploaded_count": uploaded_count,
            "database_id": target_db_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/active-adapter")
async def get_active_adapter():
    """
    Get the currently active PEFT adapter name (TB-US-035).

    Direct port of stalite3's /active-adapter endpoint — same open
    posture (no per-endpoint auth; gated by site-wide middleware).
    Reports the module-level ACTIVE_ADAPTER / ACTIVE_ADAPTER_PATH
    globals, which are populated from the TB_ACTIVE_ADAPTER env var
    at startup. Returns {"adapter": null, "adapter_path": null} if
    no adapter is configured for this deployment.
    """
    return {
        "adapter": ACTIVE_ADAPTER,
        "adapter_path": ACTIVE_ADAPTER_PATH
    }


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


@app.post("/databases/{db_id}/clear")
async def clear_specific_database(
    db_id: str,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Clear all documents from a specific database's vector store.
    Super-user-gated. For the active database, delegates to the live
    RAG system's vector store; for a non-active database, opens the
    target ChromaDB directly and clears its collection.
    """
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="This operation is disabled in demo mode")
    db_list = db_manager.list_databases()
    target = next((db for db in db_list if db['id'] == db_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Database '{db_id}' not found")
    try:
        if db_id == db_manager.active_database:
            rag_system.vector_store.clear_collection()
        else:
            from rag.vector_store import VectorStore
            VectorStore(persist_directory=target['path']).clear_collection()
        return {
            "success": True,
            "db_id": db_id,
            "name": target['name'],
            "message": f"Cleared database '{target['name']}'"
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
            llm_provider=LLM_PROVIDER,
            model_name=LLM_MODEL,
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


# Session Tracking Endpoints (TB-US-034 — direct port from stalite3)
@app.get("/sessions/my-history")
async def get_my_session_history(
    limit: int = 50,
    user_info: Dict = Depends(verify_web_auth)
):
    """
    Get session history for the authenticated user (TB-US-034).

    Args:
        limit: Maximum number of sessions to return (default: 50)

    Returns:
        List of user's past sessions
    """
    try:
        sessions = session_tracker.get_user_sessions(
            username=user_info['username'],
            limit=limit
        )
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/active")
async def get_active_sessions(user_info: Dict = Depends(verify_super_user)):
    """
    Get all currently active sessions across all users (TB-US-034).
    Requires super user privileges.
    """
    try:
        sessions = session_tracker.get_active_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/stats")
async def get_session_stats(
    username: Optional[str] = None,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get session statistics (TB-US-034).
    Requires super user privileges.

    Args:
        username: Optional username to filter stats (if omitted, returns global stats)
    """
    try:
        stats = session_tracker.get_session_stats(username)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/user/{username}")
async def get_user_session_history(
    username: str,
    limit: int = 50,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Get session history for a specific user (TB-US-034).
    Requires super user privileges.
    """
    try:
        sessions = session_tracker.get_user_sessions(
            username=username,
            limit=limit
        )
        return {"sessions": sessions}
    except Exception as e:
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
            # TB-US-017: audit failed create
            user_manager.append_audit(
                actor=user_info['username'], action='create',
                target=user_req.username,
                details={"error": result['error'], "user_type": user_req.user_type},
                success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        # TB-US-017: audit successful create
        user_manager.append_audit(
            actor=user_info['username'], action='create',
            target=user_req.username,
            details={"user_type": user_req.user_type, "email": user_req.email},
            success=True,
        )
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
    TB-US-017: self-type-change blocked.

    Args:
        username: Username to update
        type_req: New user type

    Returns:
        Update status
    """
    try:
        # TB-US-017: self-action protection — can't change own type
        if username == user_info['username']:
            user_manager.append_audit(
                actor=user_info['username'], action='change_type',
                target=username,
                details={"error": "self-action-blocked", "attempted_type": type_req.user_type},
                success=False,
            )
            raise HTTPException(
                status_code=400,
                detail="Cannot change your own user type",
            )

        # Capture current type for audit before change
        current = user_manager.get_user(username) or {}
        old_type = current.get('user_type')

        result = user_manager.update_user_type(username, type_req.user_type)

        if result['status'] == 'error':
            user_manager.append_audit(
                actor=user_info['username'], action='change_type',
                target=username, details={"error": result['error']}, success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        user_manager.append_audit(
            actor=user_info['username'], action='change_type',
            target=username,
            details={"before": old_type, "after": type_req.user_type},
            success=True,
        )
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
            user_manager.append_audit(
                actor=user_info['username'], action='reset_password',
                target=username, details={"error": result['error']}, success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        # TB-US-017: audit; new password is NOT logged
        user_manager.append_audit(
            actor=user_info['username'], action='reset_password',
            target=username, details={}, success=True,
        )
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
async def delete_or_deactivate_user(
    username: str,
    permanent: bool = False,
    user_info: Dict = Depends(verify_super_user)
):
    """
    Deactivate or hard-delete a user.
    Requires super user privileges.
    TB-US-010 default behavior preserved: soft delete (deactivate).
    TB-US-017 extension: `?permanent=true` hard-deletes the row.
    """
    try:
        # Prevent self-action (both deactivate and permanent delete)
        if username == user_info['username']:
            user_manager.append_audit(
                actor=user_info['username'],
                action='delete' if permanent else 'deactivate',
                target=username,
                details={"error": "self-action-blocked"},
                success=False,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Cannot {'delete' if permanent else 'deactivate'} your own account",
            )

        if permanent:
            result = user_manager.hard_delete_user(username)
            action = 'delete'
            msg = f"User '{username}' deleted permanently"
            details_payload = {"deleted_snapshot": result.get("deleted_snapshot")}
        else:
            result = user_manager.deactivate_user(username)
            action = 'deactivate'
            msg = f"User '{username}' deactivated successfully"
            details_payload = {}

        if result['status'] == 'error':
            user_manager.append_audit(
                actor=user_info['username'], action=action, target=username,
                details={"error": result['error']}, success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        user_manager.append_audit(
            actor=user_info['username'], action=action, target=username,
            details=details_payload, success=True,
        )
        return {"success": True, "message": msg, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TB-US-017: new endpoints for user management v2

@app.put("/users/{username}/active")
async def set_user_active(
    username: str,
    req: SetActiveRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Symmetric activate/deactivate. TB-US-017.

    Body: {"active": true | false}. True reactivates a deactivated user;
    False deactivates (soft). Self-action blocked. Audited.
    """
    try:
        # Self-action protection for deactivate (reactivating self is
        # pathologically fine but doesn't make sense; still blocked for
        # symmetry).
        if username == user_info['username']:
            action = 'activate' if req.active else 'deactivate'
            user_manager.append_audit(
                actor=user_info['username'], action=action, target=username,
                details={"error": "self-action-blocked"}, success=False,
            )
            raise HTTPException(
                status_code=400,
                detail="Cannot change active status of your own account",
            )

        if req.active:
            result = user_manager.reactivate_user(username)
            action = 'activate'
        else:
            result = user_manager.deactivate_user(username)
            action = 'deactivate'

        if result['status'] == 'error':
            user_manager.append_audit(
                actor=user_info['username'], action=action, target=username,
                details={"error": result['error']}, success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        user_manager.append_audit(
            actor=user_info['username'], action=action, target=username,
            details={}, success=True,
        )
        return {"success": True, "username": username, "active": req.active, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{username}/email")
async def update_user_email(
    username: str,
    req: UpdateEmailRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Update a user's email. TB-US-017. Empty / null clears the email."""
    try:
        result = user_manager.update_email(username, req.email)
        if result['status'] == 'error':
            user_manager.append_audit(
                actor=user_info['username'], action='update_email',
                target=username, details={"error": result['error']}, success=False,
            )
            raise HTTPException(status_code=400, detail=result['error'])

        user_manager.append_audit(
            actor=user_info['username'], action='update_email',
            target=username,
            details={"before": result.get('old_email'), "after": result.get('new_email')},
            success=True,
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/audit-log")
async def get_admin_audit_log(
    limit: int = 200,
    user_info: Dict = Depends(verify_super_user),
):
    """Return admin_audit entries newest-first. TB-US-017."""
    try:
        entries = user_manager.get_audit_log(limit=max(1, min(limit, 1000)))
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/bulk")
async def bulk_user_action(
    req: BulkActionRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Apply one admin action to many usernames. TB-US-017.

    Body:
        action: 'deactivate' | 'activate' | 'delete'
        usernames: list of usernames to apply the action to

    Returns:
        Per-user outcome map. If one user fails (self-action protection,
        not-found, etc.), the others still complete.
    """
    try:
        if req.action not in ('deactivate', 'activate', 'delete'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{req.action}'. Must be one of: deactivate, activate, delete",
            )
        if not req.usernames:
            raise HTTPException(status_code=400, detail="usernames list cannot be empty")

        actor = user_info['username']
        outcomes: Dict[str, Dict] = {}
        for target in req.usernames:
            # Self-action protection
            if target == actor:
                outcomes[target] = {"status": "error", "error": "self-action-blocked"}
                user_manager.append_audit(
                    actor=actor, action=f'bulk_{req.action}', target=target,
                    details={"error": "self-action-blocked"}, success=False,
                )
                continue

            try:
                if req.action == 'deactivate':
                    r = user_manager.deactivate_user(target)
                elif req.action == 'activate':
                    r = user_manager.reactivate_user(target)
                elif req.action == 'delete':
                    r = user_manager.hard_delete_user(target)
                else:
                    r = {"status": "error", "error": "unknown action"}

                outcomes[target] = r
                if r['status'] == 'success':
                    user_manager.append_audit(
                        actor=actor, action=f'bulk_{req.action}', target=target,
                        details={}, success=True,
                    )
                else:
                    user_manager.append_audit(
                        actor=actor, action=f'bulk_{req.action}', target=target,
                        details={"error": r.get('error')}, success=False,
                    )
            except Exception as e:
                outcomes[target] = {"status": "error", "error": str(e)}
                user_manager.append_audit(
                    actor=actor, action=f'bulk_{req.action}', target=target,
                    details={"error": str(e)}, success=False,
                )

        succeeded = sum(1 for o in outcomes.values() if o.get('status') == 'success')
        failed = len(outcomes) - succeeded
        return {
            "action": req.action,
            "total": len(outcomes),
            "succeeded": succeeded,
            "failed": failed,
            "outcomes": outcomes,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Training Set Management Endpoints (Super + Training)
@app.get("/training/sets")
async def list_training_sets(
    status: Optional[str] = None,
    search: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: Optional[int] = None,
    user_info: Dict = Depends(verify_training_or_super)
):
    """
    List training sets. Super users see all; training users see only
    those they authored (server-forced `created_by` scope).
    """
    if user_info['user_type'] == 'training':
        created_by = user_info['username']
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """
    Create a new training set. Super and training users may create;
    `created_by` is always the authenticated caller.
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """Get training set details. Training users may only fetch sets they own."""
    try:
        return _authorize_training_set(user_info, ts_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/training/sets/{ts_id}/data")
async def get_training_set_data(
    ts_id: int,
    user_info: Dict = Depends(verify_training_or_super)
):
    """Get training data. Training users may only fetch data from sets they own."""
    try:
        _authorize_training_set(user_info, ts_id)
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """Update training set metadata. Training users may only update sets they own."""
    try:
        _authorize_training_set(user_info, ts_id)
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """Delete a training set. Training users may only delete sets they own."""
    try:
        _authorize_training_set(user_info, ts_id)
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """Clone a training set. Training users may only clone sets they own; the clone is owned by them."""
    try:
        _authorize_training_set(user_info, ts_id)
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """
    Create a training set from master query log with optional filtering.
    Training users are server-scoped to their own log entries via
    `filters['username']`; super users may filter freely.
    """
    filters = dict(req.filters or {})
    if user_info['user_type'] == 'training':
        filters['username'] = user_info['username']
    try:
        result = training_manager.create_from_query_log(
            name=req.name,
            created_by=user_info['username'],
            filters=filters,
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
    user_info: Dict = Depends(verify_training_or_super)
):
    """
    Create a training set from training user ratings. Training users
    are server-scoped to their own ratings; super users may filter freely.
    """
    username_filter = req.username
    if user_info['user_type'] == 'training':
        username_filter = user_info['username']
    try:
        result = training_manager.create_from_ratings(
            name=req.name,
            created_by=user_info['username'],
            rating_filter=req.rating_filter,
            username=username_filter,
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


# ---------------------------------------------------------------------
# TB-US-052: Training-set versioning endpoints
# ---------------------------------------------------------------------

@app.get("/agents/{agent_id}/training-sets")
async def list_training_set_versions(
    agent_id: int,
    user_info: Dict = Depends(verify_web_auth),
):
    """List all versioned training-set snapshots for an agent."""
    rows = training_set_version_manager.list_versions(agent_id)
    promoted = training_set_version_manager.get_promoted(agent_id)
    return {
        "agent_id": agent_id,
        "versions": rows,
        "promoted_version_id": promoted["version_id"] if promoted else None,
    }


@app.get("/training-set-versions/{version_id}")
async def get_training_set_version(
    version_id: int,
    include_samples: bool = False,
    user_info: Dict = Depends(verify_web_auth),
):
    """Return one versioned training-set snapshot. Set include_samples=true to load the JSONL sidecar."""
    row = training_set_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Training-set version {version_id} not found")
    if include_samples:
        row = dict(row)
        row["samples"] = training_set_version_manager.read_samples(version_id)
    return row


@app.post("/training-set-versions")
async def create_training_set_version(
    req: CreateTrainingSetVersionRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Create a new draft training-set version."""
    try:
        row = training_set_version_manager.create_draft_with_samples(
            agent_id=req.agent_id,
            samples=req.samples,
            created_by=user_info["username"],
            parent_version_id=req.parent_version_id,
        )
        user_manager.append_audit(
            actor=user_info["username"],
            action="training_set_version.create_draft",
            target=str(row["version_id"]),
            details={"agent_id": req.agent_id, "sample_count": row.get("sample_count")},
            success=True,
        )
        return row
    except Exception as e:
        user_manager.append_audit(
            actor=user_info["username"],
            action="training_set_version.create_draft",
            target=None,
            details={"agent_id": req.agent_id, "error": str(e)},
            success=False,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training-set-versions/{version_id}/release")
async def release_training_set_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = training_set_version_manager.release(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.release",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.release",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/training-set-versions/{version_id}/deprecate")
async def deprecate_training_set_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = training_set_version_manager.deprecate(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.deprecate",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.deprecate",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/training-set-versions/{version_id}/promote")
async def promote_training_set_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = training_set_version_manager.promote(version_id, promoted_by=user_info["username"])
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.promote",
            target=str(version_id), details={"agent_id": row["agent_id"]}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="training_set_version.promote",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------
# TB-US-053: RAG versioning endpoints
# ---------------------------------------------------------------------

@app.get("/agents/{agent_id}/rag-versions")
async def list_rag_versions(
    agent_id: int,
    user_info: Dict = Depends(verify_web_auth),
):
    """List all versioned RAG snapshots for an agent."""
    rows = rag_version_manager.list_versions(agent_id)
    promoted = rag_version_manager.get_promoted(agent_id)
    return {
        "agent_id": agent_id,
        "versions": rows,
        "promoted_version_id": promoted["version_id"] if promoted else None,
    }


@app.get("/rag-versions/{version_id}")
async def get_rag_version(
    version_id: int,
    user_info: Dict = Depends(verify_web_auth),
):
    row = rag_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"RAG version {version_id} not found")
    return row


@app.post("/rag-versions")
async def create_rag_version(
    req: CreateRAGVersionRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Create an empty draft RAG version. Collection name is auto-assigned."""
    try:
        row = rag_version_manager.create_draft_version(
            agent_id=req.agent_id,
            created_by=user_info["username"],
            embedding_model=req.embedding_model,
            parent_version_id=req.parent_version_id,
        )
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.create_draft",
            target=str(row["version_id"]),
            details={"agent_id": req.agent_id, "collection_name": row["collection_name"]},
            success=True,
        )
        return row
    except Exception as e:
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.create_draft",
            target=None, details={"agent_id": req.agent_id, "error": str(e)}, success=False,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag-versions/{version_id}/ingest")
async def ingest_rag_docs(
    version_id: int,
    req: IngestRAGDocsRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Append documents to a draft RAG version's manifest."""
    try:
        row = rag_version_manager.ingest_docs(version_id=version_id, docs=req.docs)
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.ingest",
            target=str(version_id),
            details={"doc_count": len(req.docs), "chunk_count": row["chunk_count"]},
            success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.ingest",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rag-versions/{version_id}/release")
async def release_rag_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = rag_version_manager.release(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.release",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.release",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rag-versions/{version_id}/deprecate")
async def deprecate_rag_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = rag_version_manager.deprecate(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.deprecate",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.deprecate",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rag-versions/{version_id}/promote")
async def promote_rag_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = rag_version_manager.promote(version_id, promoted_by=user_info["username"])
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.promote",
            target=str(version_id), details={"agent_id": row["agent_id"]}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="rag_version.promote",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------
# TB-US-054: Adapter versioning endpoints
# ---------------------------------------------------------------------

@app.get("/agents/{agent_id}/adapter-versions")
async def list_adapter_versions(
    agent_id: int,
    user_info: Dict = Depends(verify_web_auth),
):
    rows = adapter_version_manager.list_versions(agent_id)
    promoted = adapter_version_manager.get_promoted(agent_id)
    return {
        "agent_id": agent_id,
        "versions": rows,
        "promoted_version_id": promoted["version_id"] if promoted else None,
    }


@app.get("/adapter-versions/{version_id}")
async def get_adapter_version(
    version_id: int,
    user_info: Dict = Depends(verify_web_auth),
):
    row = adapter_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Adapter version {version_id} not found")
    return row


@app.post("/adapter-versions/register")
async def register_adapter_version(
    req: RegisterAdapterRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Register an on-disk adapter directory as a new draft version.

    Files are copied to ``adapters/{agent_slug}/v{version_id}/``;
    ``adapter_model.safetensors`` is hashed into ``content_sha256``;
    ``adapter_config.json`` into ``config_sha256``.
    """
    try:
        row = adapter_version_manager.register_existing_adapter(
            agent_id=req.agent_id,
            agent_slug=req.agent_slug,
            source_dir=Path(req.source_dir),
            base_model=req.base_model,
            created_by=user_info["username"],
            training_set_version_id=req.training_set_version_id,
            training_run_metadata=req.training_run_metadata,
            parent_version_id=req.parent_version_id,
        )
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.register",
            target=str(row["version_id"]),
            details={
                "agent_id": req.agent_id,
                "base_model": req.base_model,
                "files_path": row["files_path"],
                "training_set_version_id": req.training_set_version_id,
            },
            success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.register",
            target=None, details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/adapter-versions/{version_id}/release")
async def release_adapter_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = adapter_version_manager.release(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.release",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.release",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/adapter-versions/{version_id}/deprecate")
async def deprecate_adapter_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = adapter_version_manager.deprecate(version_id)
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.deprecate",
            target=str(version_id), details={}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.deprecate",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/adapter-versions/{version_id}/promote")
async def promote_adapter_version(
    version_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    try:
        row = adapter_version_manager.promote(version_id, promoted_by=user_info["username"])
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.promote",
            target=str(version_id), details={"agent_id": row["agent_id"]}, success=True,
        )
        return row
    except VersionedComponentError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="adapter_version.promote",
            target=str(version_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------
# TB-US-055: Prompt + routes versioning endpoints
# ---------------------------------------------------------------------

def _audit_versioned_action(action: str, actor: str, target, details: Dict, success: bool) -> None:
    """Helper: write a versioned-component audit row best-effort."""
    user_manager.append_audit(
        actor=actor, action=action,
        target=str(target) if target is not None else None,
        details=details, success=success,
    )


# ---- Prompt endpoints ----

@app.get("/agents/{agent_id}/prompts")
async def list_prompt_versions(agent_id: int, user_info: Dict = Depends(verify_web_auth)):
    rows = prompt_version_manager.list_versions(agent_id)
    promoted = prompt_version_manager.get_promoted(agent_id)
    return {"agent_id": agent_id, "versions": rows,
            "promoted_version_id": promoted["version_id"] if promoted else None}


@app.get("/prompt-versions/{version_id}")
async def get_prompt_version(version_id: int, user_info: Dict = Depends(verify_web_auth)):
    row = prompt_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt version {version_id} not found")
    return row


@app.post("/prompt-versions")
async def create_prompt_version(req: CreatePromptVersionRequest, user_info: Dict = Depends(verify_super_user)):
    try:
        row = prompt_version_manager.create_draft_text(
            agent_id=req.agent_id, text=req.content,
            created_by=user_info["username"], parent_version_id=req.parent_version_id,
        )
        _audit_versioned_action("prompt_version.create_draft", user_info["username"], row["version_id"],
                                {"agent_id": req.agent_id, "chars": len(req.content)}, True)
        return row
    except Exception as e:
        _audit_versioned_action("prompt_version.create_draft", user_info["username"], None,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/prompt-versions/{version_id}/release")
async def release_prompt_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = prompt_version_manager.release(version_id)
        _audit_versioned_action("prompt_version.release", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("prompt_version.release", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/prompt-versions/{version_id}/deprecate")
async def deprecate_prompt_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = prompt_version_manager.deprecate(version_id)
        _audit_versioned_action("prompt_version.deprecate", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("prompt_version.deprecate", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/prompt-versions/{version_id}/promote")
async def promote_prompt_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = prompt_version_manager.promote(version_id, promoted_by=user_info["username"])
        _audit_versioned_action("prompt_version.promote", user_info["username"], version_id,
                                {"agent_id": row["agent_id"]}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("prompt_version.promote", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


# ---- Routes endpoints ----

@app.get("/agents/{agent_id}/routes")
async def list_route_versions(agent_id: int, user_info: Dict = Depends(verify_web_auth)):
    rows = route_version_manager.list_versions(agent_id)
    promoted = route_version_manager.get_promoted(agent_id)
    return {"agent_id": agent_id, "versions": rows,
            "promoted_version_id": promoted["version_id"] if promoted else None}


@app.get("/route-versions/{version_id}")
async def get_route_version(version_id: int, user_info: Dict = Depends(verify_web_auth)):
    row = route_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Route version {version_id} not found")
    return row


@app.post("/route-versions")
async def create_route_version(req: CreateRouteVersionRequest, user_info: Dict = Depends(verify_super_user)):
    try:
        row = route_version_manager.create_draft_routes(
            agent_id=req.agent_id, routes=req.routes,
            created_by=user_info["username"], parent_version_id=req.parent_version_id,
        )
        _audit_versioned_action("route_version.create_draft", user_info["username"], row["version_id"],
                                {"agent_id": req.agent_id, "route_count": len(req.routes)}, True)
        return row
    except Exception as e:
        _audit_versioned_action("route_version.create_draft", user_info["username"], None,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/route-versions/{version_id}/release")
async def release_route_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = route_version_manager.release(version_id)
        _audit_versioned_action("route_version.release", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("route_version.release", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/route-versions/{version_id}/deprecate")
async def deprecate_route_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = route_version_manager.deprecate(version_id)
        _audit_versioned_action("route_version.deprecate", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("route_version.deprecate", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/route-versions/{version_id}/promote")
async def promote_route_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = route_version_manager.promote(version_id, promoted_by=user_info["username"])
        _audit_versioned_action("route_version.promote", user_info["username"], version_id,
                                {"agent_id": row["agent_id"]}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("route_version.promote", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------
# TB-US-048: Agent CRUD endpoints
# ---------------------------------------------------------------------

@app.get("/agents")
async def list_agents(
    include_retired: bool = True,
    user_info: Dict = Depends(verify_web_auth),
):
    """List all agents. Any authenticated user can read."""
    return {"agents": agent_manager.list_agents(include_retired=include_retired)}


@app.get("/agents/{name}")
async def get_agent(name: str, user_info: Dict = Depends(verify_web_auth)):
    row = agent_manager.get_by_name(name)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    return row


@app.post("/agents")
async def create_agent(req: CreateAgentRequest, user_info: Dict = Depends(verify_super_user)):
    """Create a new agent. Super-only."""
    try:
        row = agent_manager.create_agent(
            name=req.name,
            display_name=req.display_name,
            description=req.description,
        )
        _audit_versioned_action("agent.create", user_info["username"], req.name,
                                {"display_name": req.display_name}, True)
        return row
    except AgentError as e:
        _audit_versioned_action("agent.create", user_info["username"], req.name,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/agents/{name}")
async def update_agent(name: str, req: UpdateAgentRequest, user_info: Dict = Depends(verify_super_user)):
    """Rename / update description / flip state. Super-only."""
    try:
        row = agent_manager.get_by_name(name)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

        actions: List[Dict] = []

        # Rename first so subsequent sets use the new name.
        current_name = name
        if req.new_name and req.new_name != current_name:
            row = agent_manager.rename_agent(current_name, req.new_name)
            actions.append({"rename": {"from": current_name, "to": req.new_name}})
            current_name = req.new_name

        if req.description is not None or req.display_name is not None:
            row = agent_manager.update_description(
                current_name,
                description=req.description,
                display_name=req.display_name,
            )
            actions.append({"metadata_update": {
                "description": req.description, "display_name": req.display_name,
            }})

        if req.state is not None:
            if req.state == "active":
                row = agent_manager.reactivate_agent(current_name)
                actions.append({"reactivate": True})
            elif req.state == "retired":
                row = agent_manager.retire_agent(current_name)
                actions.append({"retire": True})
            else:
                raise AgentError(f"Invalid state '{req.state}' (expected 'active' or 'retired')")

        _audit_versioned_action("agent.update", user_info["username"], current_name,
                                {"actions": actions}, True)
        return row
    except AgentError as e:
        _audit_versioned_action("agent.update", user_info["username"], name,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/agents/{name}")
async def delete_agent(name: str, user_info: Dict = Depends(verify_super_user)):
    """Soft-retire. Super-only. Row preserved; versions remain accessible."""
    try:
        row = agent_manager.retire_agent(name)
        _audit_versioned_action("agent.retire", user_info["username"], name, {}, True)
        return row
    except AgentError as e:
        _audit_versioned_action("agent.retire", user_info["username"], name,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------
# TB-US-063: API key management
# ---------------------------------------------------------------------

async def verify_api_key(authorization: Optional[str] = Header(None)) -> Dict:
    """Authenticate a request via a managed API key (`Authorization:
    Bearer tbk_...`). Updates `last_used_at` on match. Returns a
    user-info-like dict so route handlers can share the shape with
    session-authenticated callers.

    Not wired into existing endpoints yet (operator decides per-route
    which to open to API-key auth in a future story); this dependency
    exists so new endpoints can start requiring it and so TB-US-063's
    acceptance tests can exercise it directly.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="API key required")
    raw_key = authorization[len("Bearer "):].strip()
    row = api_key_manager.verify(raw_key)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return {
        "username": row["created_by"],   # key inherits creator identity
        "user_type": "super",             # keys currently super-scoped (per TB-US-063 §DesignNotes)
        "via_api_key": row["id"],
        "api_key_label": row["label"],
    }


@app.get("/api-keys")
async def list_api_keys(
    include_revoked: bool = True,
    user_info: Dict = Depends(verify_super_user),
):
    """List all API keys. Super-only. Raw key never returned."""
    return {"keys": api_key_manager.list_keys(include_revoked=include_revoked)}


@app.post("/api-keys")
async def create_api_key(
    req: CreateApiKeyRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Create an API key. Super-only. Raw key returned ONCE in response — never retrievable again."""
    try:
        row = api_key_manager.create_key(label=req.label, created_by=user_info["username"])
        user_manager.append_audit(
            actor=user_info["username"], action="create_api_key",
            target=str(row["id"]),
            details={"label": row["label"], "key_prefix": row["key_prefix"]},
            success=True,
        )
        return row  # raw_key field present ONLY in this response
    except ApiKeyError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="create_api_key",
            target=None, details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    """Revoke (soft) an API key. Super-only. Row preserved."""
    try:
        row = api_key_manager.revoke(key_id)
        user_manager.append_audit(
            actor=user_info["username"], action="revoke_api_key",
            target=str(key_id),
            details={"label": row.get("label"), "key_prefix": row.get("key_prefix")},
            success=True,
        )
        return row
    except ApiKeyError as e:
        user_manager.append_audit(
            actor=user_info["username"], action="revoke_api_key",
            target=str(key_id), details={"error": str(e)}, success=False,
        )
        raise HTTPException(status_code=404, detail=str(e))


# Smoke-test endpoint for the verify_api_key dependency. Any caller
# with a valid Bearer tbk_... reaches here; session cookies don't.
@app.get("/api-keys/_whoami")
async def api_key_whoami(user_info: Dict = Depends(verify_api_key)):
    """Returns the caller's identity when authenticated via API key.
    Useful for operators to verify a freshly-issued key before wiring
    it into their scripts."""
    return user_info


# ---------------------------------------------------------------------
# TB-US-056: Harness versioning + experiment CRUD + runner
# ---------------------------------------------------------------------

# ---- Harness lifecycle (no promote — harness is not Sweet Spot) ----

@app.get("/agents/{agent_id}/harnesses")
async def list_harness_versions(agent_id: int, user_info: Dict = Depends(verify_web_auth)):
    rows = harness_version_manager.list_versions(agent_id)
    return {"agent_id": agent_id, "versions": rows}


@app.get("/harness-versions/{version_id}")
async def get_harness_version(version_id: int, user_info: Dict = Depends(verify_web_auth)):
    row = harness_version_manager.get_by_id(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Harness version {version_id} not found")
    return row


@app.post("/harness-versions")
async def create_harness_version(req: CreateHarnessVersionRequest, user_info: Dict = Depends(verify_super_user)):
    try:
        row = harness_version_manager.create_draft_definition(
            agent_id=req.agent_id, definition=req.definition,
            created_by=user_info["username"], parent_version_id=req.parent_version_id,
        )
        _audit_versioned_action("harness_version.create_draft", user_info["username"], row["version_id"],
                                {"agent_id": req.agent_id, "module": req.definition.get("module")}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("harness_version.create_draft", user_info["username"], None,
                                {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/harness-versions/{version_id}/release")
async def release_harness_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = harness_version_manager.release(version_id)
        _audit_versioned_action("harness_version.release", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("harness_version.release", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/harness-versions/{version_id}/deprecate")
async def deprecate_harness_version(version_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = harness_version_manager.deprecate(version_id)
        _audit_versioned_action("harness_version.deprecate", user_info["username"], version_id, {}, True)
        return row
    except VersionedComponentError as e:
        _audit_versioned_action("harness_version.deprecate", user_info["username"], version_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


# ---- Experiment CRUD ----

@app.get("/experiments")
async def list_experiments(
    agent_id: Optional[int] = None,
    user_info: Dict = Depends(verify_web_auth),
):
    rows = experiment_manager.list_experiments(agent_id=agent_id)
    return {"experiments": rows, "agent_id": agent_id}


@app.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: int, user_info: Dict = Depends(verify_web_auth)):
    row = experiment_manager.get_by_id(experiment_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return row


@app.post("/experiments")
async def create_experiment(req: CreateExperimentRequest, user_info: Dict = Depends(verify_super_user)):
    try:
        row = experiment_manager.create_experiment(
            agent_id=req.agent_id,
            label=req.label,
            created_by=user_info["username"],
            system_prompt_version_id=req.system_prompt_version_id,
            rag_version_id=req.rag_version_id,
            llm_identifier=req.llm_identifier,
            adapter_version_id=req.adapter_version_id,
            harness_version_id=req.harness_version_id,
            parent_experiment_id=req.parent_experiment_id,
        )
        _audit_versioned_action("experiment.create", user_info["username"], row["experiment_id"],
                                {"agent_id": req.agent_id, "label": req.label}, True)
        return row
    except Exception as e:
        _audit_versioned_action("experiment.create", user_info["username"], None, {"error": str(e)}, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experiments/{experiment_id}/run")
async def run_experiment_endpoint(
    experiment_id: int,
    background_tasks: BackgroundTasks,
    user_info: Dict = Depends(verify_super_user),
):
    """Transition draft → running and schedule the harness runner."""
    try:
        row = experiment_manager.transition_state(experiment_id, "running")
    except ExperimentError as e:
        _audit_versioned_action("experiment.run", user_info["username"], experiment_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))

    def _run_in_background():
        try:
            _harness_runner.run_experiment(experiment_id)
        except Exception as e:
            # Already logged and archived inside run_experiment; swallow here
            # so background task doesn't bubble into FastAPI logs twice.
            pass

    background_tasks.add_task(_run_in_background)
    _audit_versioned_action("experiment.run", user_info["username"], experiment_id,
                            {"state": row["state"]}, True)
    return row


@app.post("/experiments/{experiment_id}/archive")
async def archive_experiment(experiment_id: int, user_info: Dict = Depends(verify_super_user)):
    try:
        row = experiment_manager.transition_state(experiment_id, "archived")
        _audit_versioned_action("experiment.archive", user_info["username"], experiment_id, {}, True)
        return row
    except ExperimentError as e:
        _audit_versioned_action("experiment.archive", user_info["username"], experiment_id, {"error": str(e)}, False)
        raise HTTPException(status_code=400, detail=str(e))


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


# ---------------------------------------------------------------------
# TB-US-065: launch + cancel endpoints (background training subprocess)
# ---------------------------------------------------------------------

@app.post("/training/runs/launch")
async def launch_training_run(
    req: LaunchTrainingRunRequest,
    user_info: Dict = Depends(verify_super_user),
):
    """Spawn `training/math/train.py --run-id <id>` as a detached
    subprocess. Enforces single-slot queue (409 if another is running).
    Returns the created row id + PID. Progress is written to the
    tracker DB directly by train.py.
    """
    import subprocess
    import sys as _sys
    from pathlib import Path as _Path

    # R2: enforce single-slot
    active = training_run_tracker.get_active_run()
    if active is not None:
        _audit_versioned_action(
            "training_run.launch", user_info["username"], None,
            {"error": "another run active", "active_run_id": active["id"]}, False,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "another training run is already active",
                "active_run_id": active["id"],
                "active_run_name": active["run_name"],
                "active_run_started_at": active["started_at"],
            },
        )

    # Default adapter output path — operator can override via config
    adapter_output_path = req.hyperparameters.get(
        "adapter_output_path",
        f"training/adapters/{req.run_name}",
    )

    # R3: create DB row BEFORE spawn
    try:
        row = training_run_tracker.create_launched_run(
            run_name=req.run_name,
            description=req.description,
            base_model=req.base_model,
            adapter_output_path=adapter_output_path,
            config={**req.hyperparameters, "base_model": req.base_model},
            created_by=user_info["username"],
            agent_id=req.agent_id,
            training_set_version_id=req.training_set_version_id,
            notes=req.notes,
        )
    except Exception as e:
        _audit_versioned_action(
            "training_run.launch", user_info["username"], None,
            {"error": str(e), "stage": "create_row"}, False,
        )
        raise HTTPException(status_code=400, detail=str(e))

    run_id = row["id"]
    repo_root = _Path(__file__).resolve().parent.parent.parent
    train_script = repo_root / "training" / "math" / "train.py"

    # R4: spawn detached subprocess. stdout/stderr → DEVNULL since
    # train.py writes logs directly to the tracker DB (R7).
    try:
        proc = subprocess.Popen(
            [
                _sys.executable, str(train_script),
                "--run-id", str(run_id),
            ],
            cwd=str(repo_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        # Clean up the row we just created
        training_run_tracker.update_training_run_status(
            run_id, status="failed",
            notes=f"spawn failed: {e}",
        )
        _audit_versioned_action(
            "training_run.launch", user_info["username"], str(run_id),
            {"error": str(e), "stage": "spawn"}, False,
        )
        raise HTTPException(status_code=500, detail=f"subprocess spawn failed: {e}")

    training_run_tracker.set_run_pid(run_id, proc.pid)
    _audit_versioned_action(
        "training_run.launch", user_info["username"], str(run_id),
        {"run_name": req.run_name, "pid": proc.pid, "agent_id": req.agent_id,
         "training_set_version_id": req.training_set_version_id},
        True,
    )
    return {
        "run_id": run_id,
        "status": "running",
        "pid": proc.pid,
        "started_at": row["started_at"],
    }


@app.post("/training/runs/{run_id}/cancel")
async def cancel_training_run(
    run_id: int,
    user_info: Dict = Depends(verify_super_user),
):
    """SIGTERM → SIGKILL fallback. Flips status to 'stopped'. Partial
    checkpoint files remain on disk for forensics.
    """
    result = training_run_tracker.cancel_run(run_id, cancelled_by=user_info["username"])
    if result.get("status") == "error":
        _audit_versioned_action(
            "training_run.cancel", user_info["username"], str(run_id),
            {"error": result.get("error")}, False,
        )
        raise HTTPException(status_code=400, detail=result.get("error"))
    _audit_versioned_action(
        "training_run.cancel", user_info["username"], str(run_id),
        {"signals": result.get("signals")}, True,
    )
    return {"success": True, **result}


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


# TB-US-019: Training session workflow (ported from stalite3) + training set export

def _training_session_file(username: str) -> Path:
    """Per-user session JSON lives at logs/training_sessions/session_<u>.json."""
    session_dir = Path("logs/training_sessions")
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / f"session_{username}.json"


def _load_training_session(username: str) -> Dict:
    """Load the user's session file, or return the empty-state dict."""
    f = _training_session_file(username)
    if not f.exists():
        return {"active_session": None, "completed_sessions": []}
    try:
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"active_session": None, "completed_sessions": []}


def _save_training_session(username: str, data: Dict) -> None:
    f = _training_session_file(username)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


@app.get("/training/session")
async def get_training_session(user_info: Dict = Depends(verify_web_auth)):
    """Return the current user's `{active_session, completed_sessions}`.

    Non-training users get the empty-state response (not 403) — matches
    stalite3's behavior per TB-US-019 R1.
    """
    try:
        if user_info.get("user_type") != "training":
            return {"active_session": None, "completed_sessions": []}
        return _load_training_session(user_info["username"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/session")
async def save_training_session(
    session_req: TrainingSessionRequest,
    user_info: Dict = Depends(verify_web_auth),
):
    """Save/update the current user's active session.

    `started_at` is preserved across saves (stamped on first write only).
    Non-training users receive HTTP 403.
    """
    if user_info.get("user_type") != "training":
        raise HTTPException(
            status_code=403,
            detail="Only training users can save training sessions",
        )
    try:
        username = user_info["username"]
        data = _load_training_session(username)
        existing_started_at = None
        if data.get("active_session"):
            existing_started_at = data["active_session"].get("started_at")
        started_at = existing_started_at or datetime.utcnow().isoformat() + "Z"

        data["active_session"] = {
            "session_name": session_req.session_name,
            "session_state": session_req.session_state,
            "record_count": session_req.record_count,
            "started_at": started_at,
        }
        _save_training_session(username, data)
        return {"success": True, "active_session": data["active_session"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/training/session/complete")
async def complete_training_session(
    session_req: TrainingSessionRequest,
    user_info: Dict = Depends(verify_web_auth),
):
    """Mark the active session as completed and move it to the completed list."""
    if user_info.get("user_type") != "training":
        raise HTTPException(
            status_code=403,
            detail="Only training users can complete training sessions",
        )
    try:
        username = user_info["username"]
        data = _load_training_session(username)
        active = data.get("active_session") or {}
        started_at = active.get("started_at")

        completed_at = datetime.utcnow().isoformat() + "Z"
        completed_entry = {
            "session_name": session_req.session_name,
            "session_state": "completed",
            "record_count": session_req.record_count,
            "started_at": started_at,
            "completed_at": completed_at,
        }
        completed_list = data.get("completed_sessions") or []
        completed_list.append(completed_entry)

        data["active_session"] = None
        data["completed_sessions"] = completed_list
        _save_training_session(username, data)

        return {"success": True, "completed_session": completed_entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _sanitize_filename_part(s: str) -> str:
    """Keep only alphanumerics, dash, underscore; collapse others to '_'."""
    import re as _re
    out = _re.sub(r"[^A-Za-z0-9_-]+", "_", s or "").strip("_")
    return out or "ts"


def _format_training_example(example: Dict, fmt: str) -> Dict:
    """Transform an in-storage example into the requested export format.

    'alpaca'  → {instruction, input, output, ...}
    'chatml'  → {messages: [{role, content}, ...]}
    'raw'     → the example dict as-is
    """
    if fmt == "raw":
        return example
    # Pull canonical fields; TB stores examples as {instruction, input, output}
    instruction = example.get("instruction") or example.get("question") or ""
    input_val = example.get("input") or ""
    output = example.get("output") or example.get("answer") or ""
    if fmt == "alpaca":
        row = {
            "instruction": instruction,
            "input": input_val,
            "output": output,
        }
        # Preserve optional metadata if present (model, timestamp, etc.)
        for optional in ("model", "timestamp", "rating"):
            if optional in example and example[optional] is not None:
                row[optional] = example[optional]
        return row
    if fmt == "chatml":
        user_content = instruction
        if input_val:
            user_content = f"{instruction}\n\n{input_val}" if instruction else input_val
        return {
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": output},
            ]
        }
    return example


@app.get("/training/sets/{ts_id}/export")
async def export_training_set(
    ts_id: int,
    format: str = "alpaca",
    rating: Optional[str] = None,
    user_info: Dict = Depends(verify_web_auth),
):
    """Export a training set as a JSONL file. Formats: alpaca, chatml, raw.

    Role gating: training users can only export sets they created
    (TB-US-011 ownership pattern); super users can export any set.

    `rating` query param returns HTTP 400 — TB's training set example
    rows don't carry a rating field. (See TB-US-019 Design Notes:
    "strict" option chosen since TB schema doesn't expose rating at
    the example level.)
    """
    # Format validation (AC9)
    valid_formats = ("alpaca", "chatml", "raw")
    if format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}",
        )
    if rating is not None:
        raise HTTPException(
            status_code=400,
            detail="TB training sets don't carry a per-example rating; the 'rating' filter isn't supported. Use the ratings subsystem to build a filtered training set via POST /training/sets/from-ratings.",
        )

    # Fetch metadata + ownership check
    ts_meta = training_manager.get_training_set(ts_id)
    if not ts_meta:
        raise HTTPException(status_code=404, detail=f"Training set {ts_id} not found")

    user_type = user_info.get("user_type")
    username = user_info["username"]
    if user_type == "super":
        pass  # super can export any
    elif user_type == "training":
        if ts_meta.get("created_by") != username:
            raise HTTPException(
                status_code=403,
                detail="You can only export training sets you created",
            )
    else:
        raise HTTPException(status_code=403, detail="Insufficient privileges to export training sets")

    # Load examples
    examples = training_manager.get_training_data(ts_id) or []

    # Build filename
    date_part = datetime.now().strftime("%Y%m%d")
    name_part = _sanitize_filename_part(ts_meta.get("name") or f"ts_{ts_id}")
    filename = f"{name_part}-{format}-{date_part}.jsonl"

    def _generate():
        for ex in examples:
            row = _format_training_example(ex, format)
            yield json.dumps(row, ensure_ascii=False) + "\n"

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Documentation Endpoints
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules', '.pytest_cache'}
# Root-level files that are repo-management artifacts (git-convention
# README, project backlog) — kept in the repo but hidden from the
# user-facing docs page. INSTALL.md stays visible — it's operator setup.
EXCLUDE_FILES = {'README.md', 'BACKLOG.md'}

@app.get("/docs/list")
async def list_docs(user_info: Dict = Depends(verify_web_auth)):
    """List all markdown files in the project."""
    try:
        md_files = []
        for path in sorted(Path(PROJECT_ROOT).rglob("*.md")):
            # Skip excluded directories
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            # Skip project-management artifacts at the repo root (keep
            # files in deeper dirs even if named README.md — e.g., a
            # per-folder README is fine).
            if path.parent == Path(PROJECT_ROOT) and path.name in EXCLUDE_FILES:
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
