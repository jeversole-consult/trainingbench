"""
TrainingBench - Version Information

This file tracks the application version using semantic versioning.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
__build_date__ = "2026-02-15"
__description__ = "ML Training Platform - Complete training lifecycle management"

# Feature set at this version
FEATURES = {
    "multi_database_support": True,
    "database_duplication": True,
    "comparison_tool": True,
    "voice_interface": True,
    "document_processing": {
        "pdf": True,
        "docx": True,
        "xlsx": True,
        "images_ocr": True,
        "text": True
    },
    "gpu_acceleration": True,
    "web_authentication": True,
    "session_tracking": True,
    "query_logging": True,
    "folder_organization": True,
    "ml_training_platform": {
        "master_query_log": True,
        "training_set_manager": True,
        "training_run_tracker": True,
        "experiment_tracking": True,
        "real_time_progress": True,
        "checkpoint_management": True,
        "run_comparison": True,
        "automatic_logging": True,
        "training_set_viewer": True,
        "session_to_set_completion": True
    }
}

# Technical stack
TECH_STACK = {
    "backend": "FastAPI",
    "vector_db": "ChromaDB",
    "embeddings": "sentence-transformers (all-MiniLM-L6-v2)",
    "llm": "Ollama (llama3.1:8b)",
    "frontend": "Vanilla JavaScript",
    "gpu": "CUDA (NVIDIA RTX 3090)"
}

def get_version():
    """Return version string."""
    return __version__

def get_version_info():
    """Return detailed version information."""
    return {
        "version": __version__,
        "build_date": __build_date__,
        "description": __description__,
        "features": FEATURES,
        "tech_stack": TECH_STACK
    }
