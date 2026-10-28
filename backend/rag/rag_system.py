"""
RAG system using LangChain for question answering.

The RAGSystem class plugs together:
  - a VectorStore for retrieval
  - one of several LLM providers for generation
  - optional caller-supplied hooks for queries the LLM is poor at
    (e.g. an exact-arithmetic calculator, or a structured-extraction
    handler) — see `calculator` and `specialized_handler` constructor
    parameters.

All defaults are environment-overridable so the same code can run in
research, demo, and production deployments without source edits.
"""

from typing import Callable, List, Dict, Optional
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import HuggingFacePipeline
from .vector_store import VectorStore
from .document_processor import DocumentProcessor
from .query_logger import QueryLogger
from datetime import datetime
import hashlib
import json
import os
import re  # TB-US-040: query-route pattern compilation


# Provider-specific default model identifiers (env-overridable).
DEFAULT_PEFT_ADAPTER_PATH = os.getenv("PEFT_ADAPTER_PATH", "training/adapters/example")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Generation sampling params (env-overridable).
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
LLM_TOP_K = int(os.getenv("LLM_TOP_K", "40"))
LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "512"))

# Document chunking config (env-overridable).
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))

# Default prompt template. Override via the `prompt_template` constructor
# argument or by subclassing if your domain needs different framing.
DEFAULT_RAG_PROMPT = """Use the following context from documents to answer the question. If the context contains relevant information, use it. Otherwise, answer from your training.

Context:
{context}

Question: {question}

Answer:"""


# Type alias for the optional plug-in hooks below.
# A hook takes a question (str) and returns either an answer string
# (signalling "I handled this") or None (signalling "fall through to
# the LLM").
QueryHook = Callable[[str], Optional[str]]


class RAGSystem:
    """Complete RAG system for question answering over ingested content."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_provider: str = "huggingface",
        model_name: Optional[str] = None,
        enable_logging: bool = True,
        calculator: Optional[QueryHook] = None,
        specialized_handler: Optional[QueryHook] = None,
        prompt_template: Optional[str] = None,
    ):
        """
        Initialize the RAG system.

        Args:
            vector_store: Vector store instance (creates default if None)
            llm_provider: LLM provider to use ('huggingface', 'openai',
                'ollama', 'peft', etc.)
            model_name: Identifier of the model to use (adapter path for
                peft, model tag for ollama, etc.). Falls back to a
                provider-specific default if None.
            enable_logging: Whether to log queries for training data
                collection.
            calculator: Optional hook for questions better answered by
                an exact computation than by the LLM. Signature:
                question (str) -> answer (str) | None. Return None to
                fall through to the LLM.
            specialized_handler: Optional hook for queries that need
                structured extraction or domain-specific handling.
                Same signature as `calculator`.
            prompt_template: Optional prompt template string with
                `{context}` and `{question}` placeholders. Falls back
                to `DEFAULT_RAG_PROMPT`.
        """
        self.vector_store = vector_store or VectorStore()
        self.document_processor = DocumentProcessor()
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.calculator = calculator
        self.specialized_handler = specialized_handler

        # Initialize query logger
        self.query_logger = QueryLogger() if enable_logging else None
        self.enable_logging = enable_logging

        # Folder management file
        self.folders_file = os.path.join(
            self.vector_store.persist_directory,
            "folders.json"
        )

        # Initialize LLM (provider is selected at construction time)
        self.llm = None
        self._init_llm(llm_provider, model_name)

        # Prompt template — caller may override; TB-US-040 may update
        # this from AppSettings on each query via _refresh_prompt_template.
        self._template_str = prompt_template or DEFAULT_RAG_PROMPT
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=self._template_str,
        )

        # TB-US-040: query routes cache (loaded lazily from AppSettings).
        # _routes_str holds the JSON serialization of the last-seen routes
        # list for change detection; _compiled_routes holds the compiled
        # (name, [patterns], augmentation, position) tuples.
        self._routes_str: str = ""
        self._compiled_routes: List = []

    def _refresh_prompt_template(self) -> None:
        """TB-US-040: Reload the prompt template from AppSettings if changed.

        Fail-soft: AppSettings import error or missing value falls through to
        the init-time template. Caches the last-seen template string so we
        only rebuild the LangChain PromptTemplate when the stored value
        actually changes.
        """
        try:
            from api.app_settings import AppSettings
            current = AppSettings.rag_prompt()
        except Exception as e:
            print(f"rag_system: could not load prompt from AppSettings ({e}); using built-in fallback")
            try:
                from api.app_settings import DEFAULT_RAG_PROMPT as APPSETTINGS_DEFAULT
                current = APPSETTINGS_DEFAULT
            except Exception:
                current = self._template_str  # last-known good
        if current != self._template_str:
            self.prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template=current,
            )
            self._template_str = current

    def _refresh_query_routes(self) -> None:
        """TB-US-040: Reload query routes from AppSettings and recompile patterns if changed.

        Fail-soft: on AppSettings error, route augmentation is skipped entirely
        (empty compiled list). Routes with `enabled: false` are skipped.
        Routes with malformed regex patterns are silently skipped and logged.
        """
        try:
            from api.app_settings import AppSettings
            current = AppSettings.query_routes()
        except Exception as e:
            print(f"rag_system: could not load query routes ({e}); skipping rewrite layer")
            self._compiled_routes = []
            self._routes_str = ""
            return

        current_str = json.dumps(current, sort_keys=True)
        if current_str == self._routes_str:
            return

        compiled = []
        for route in current:
            if not isinstance(route, dict) or not route.get("enabled", True):
                continue
            try:
                patterns = [
                    re.compile(p, re.IGNORECASE)
                    for p in route.get("patterns", [])
                    if isinstance(p, str) and p
                ]
            except re.error as e:
                print(f"rag_system: skipping route '{route.get('name')}' due to regex error: {e}")
                continue
            if not patterns:
                continue
            compiled.append((
                route.get("name", "unnamed"),
                patterns,
                route.get("augmentation", ""),
                route.get("augmentation_position", "prefix"),
            ))
        self._compiled_routes = compiled
        self._routes_str = current_str

    def _maybe_augment_query(self, question: str) -> tuple:
        """TB-US-040: Apply the first matching query route to the search string.

        Returns (search_query, matched_route_name). If no route matches, the
        search query is unchanged and matched_route_name is None.

        Note: the ORIGINAL question goes to the LLM; only the retrieval
        similarity-search query is augmented. The augmentation is a
        retrieval hint, not a question rewrite.
        """
        self._refresh_query_routes()
        for name, patterns, augmentation, position in self._compiled_routes:
            for pattern in patterns:
                if pattern.search(question):
                    if position == "suffix":
                        augmented = f"{question} {augmentation}".strip()
                    else:
                        augmented = f"{augmentation}{question}"
                    return augmented, name
        return question, None

    def _init_llm(self, provider: str, model_name: Optional[str]):
        """Initialize the LLM based on provider."""
        if provider == "openai":
            # Requires OPENAI_API_KEY in environment
            try:
                from langchain_community.llms import OpenAI
                self.llm = OpenAI(
                    temperature=LLM_TEMPERATURE,
                    model_name=model_name or DEFAULT_OPENAI_MODEL,
                )
                print("Using OpenAI LLM")
            except Exception as e:
                print(f"Failed to initialize OpenAI: {e}")
                print("You need to set OPENAI_API_KEY environment variable")
                self.llm = None
        elif provider == "ollama":
            # Local Ollama-served model
            try:
                from langchain_ollama import OllamaLLM
                model = model_name or DEFAULT_OLLAMA_MODEL
                self.llm = OllamaLLM(
                    model=model,
                    base_url=OLLAMA_BASE_URL,
                    temperature=LLM_TEMPERATURE,
                )
                print(f"Using Ollama LLM: {model} (base_url={OLLAMA_BASE_URL})")
            except Exception as e:
                print(f"Failed to initialize Ollama: {e}")
                print("Make sure Ollama is installed and running, then:")
                print(f"  ollama pull {model_name or DEFAULT_OLLAMA_MODEL}")
                self.llm = None
        elif provider == "peft" or provider == "huggingface_peft":
            # PEFT adapter via HuggingFace
            try:
                import torch
                from peft import AutoPeftModelForCausalLM
                from transformers import AutoTokenizer, pipeline
                from langchain_community.llms import HuggingFacePipeline

                adapter_path = model_name or DEFAULT_PEFT_ADAPTER_PATH

                if not os.path.exists(adapter_path):
                    print(f"Error: PEFT adapter not found at {adapter_path}")
                    print("Train an adapter first, then set PEFT_ADAPTER_PATH or")
                    print("pass model_name=... to the RAGSystem constructor.")
                    self.llm = None
                    return

                print(f"Loading PEFT adapter from {adapter_path}...")
                print("(This may take a minute...)")

                model = AutoPeftModelForCausalLM.from_pretrained(
                    adapter_path,
                    device_map="auto",
                    torch_dtype=torch.float16,
                )
                tokenizer = AutoTokenizer.from_pretrained(adapter_path)

                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token

                pipe = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=LLM_MAX_NEW_TOKENS,
                    temperature=LLM_TEMPERATURE,
                    do_sample=True,
                    top_p=LLM_TOP_P,
                    top_k=LLM_TOP_K,
                )

                self.llm = HuggingFacePipeline(pipeline=pipe)
                print(f"Using PEFT adapter: {adapter_path}")

            except ImportError as e:
                print(f"Failed to initialize PEFT: {e}")
                print("Install PEFT dependencies:")
                print("  pip install peft transformers accelerate torch")
                self.llm = None
            except Exception as e:
                print(f"Failed to initialize PEFT: {e}")
                self.llm = None
        elif provider == "huggingface":
            # Placeholder — configure a concrete provider for real use
            print("Note: For production use, configure a concrete LLM provider")
            print("(set LLM_PROVIDER=peft|ollama|openai).")
            self.llm = None
        else:
            print(f"Unknown provider: {provider}")
            self.llm = None

    def ingest_scraped_data(self, scraped_data: List[Dict]) -> None:
        """Ingest scraped data into the RAG system."""
        print("Processing scraped data for RAG...")
        documents = self.document_processor.prepare_documents_for_rag(scraped_data)
        self.vector_store.add_documents(documents)
        print("Successfully ingested data into RAG system")

    def query(self, question: str, k: int = 4, rating: Optional[int] = None) -> Dict:
        """
        Query the RAG system with a question.

        Resolution order:
          1. Optional caller-supplied `calculator` hook
          2. Optional caller-supplied `specialized_handler` hook
          3. Vector-store retrieval + LLM generation

        Args:
            question: Question to answer
            k: Number of relevant documents to retrieve
            rating: Optional rating for this query (1-5) for training
                data quality

        Returns:
            Dictionary containing answer, sources, and context.
        """
        # 1. Optional plug-in: calculator (e.g. exact arithmetic)
        if self.calculator is not None:
            calc_answer = self.calculator(question)
            if calc_answer:
                return {
                    "answer": calc_answer,
                    "sources": [],
                    "context": [],
                    "plugin": "calculator",
                }

        # 2. Optional plug-in: specialized handler (e.g. structured extraction)
        if self.specialized_handler is not None:
            handler_answer = self.specialized_handler(question)
            if handler_answer:
                return {
                    "answer": handler_answer,
                    "sources": [],
                    "context": [],
                    "plugin": "specialized_handler",
                }

        # 3. Retrieval + generation
        # TB-US-040: apply configured query-route augmentation to the
        # retrieval query before similarity search. The ORIGINAL question
        # still goes to the LLM.
        search_query, matched_route = self._maybe_augment_query(question)
        if matched_route:
            print(f"query_routes: matched '{matched_route}', augmented search = {search_query!r}")
        relevant_docs = self.vector_store.similarity_search(search_query, k=k)
        context = "\n\n".join([doc["content"] for doc in relevant_docs]) if relevant_docs else ""

        if self.llm:
            # TB-US-040: pick up any operator-updated RAG prompt from
            # AppSettings before invoking the LLM.
            self._refresh_prompt_template()
            prompt = self.prompt_template.format(context=context, question=question)
            answer = self.llm.invoke(prompt)

            # Strip the prompt prefix some pipelines echo back
            if isinstance(answer, str) and "Answer:" in answer:
                answer = answer.split("Answer:", 1)[1].strip()
        else:
            if not relevant_docs:
                return {
                    "answer": "I couldn't find any relevant information to answer your question.",
                    "sources": [],
                    "context": [],
                }
            answer = f"[LLM not configured - showing relevant context]\n\n{context[:500]}..."

        # Extract sources
        sources = []
        for doc in relevant_docs:
            source_info = {
                "url": doc["metadata"].get("source", "Unknown"),
                "title": doc["metadata"].get("title", "Unknown"),
                "relevance_score": 1 - doc["distance"] if doc["distance"] else None,
                "content": doc["content"],
            }
            if source_info not in sources:
                sources.append(source_info)

        result = {
            "answer": answer,
            "sources": sources,
            "context": [doc["content"] for doc in relevant_docs],
        }

        if self.query_logger:
            self.query_logger.log_interaction(
                question=question,
                context=[doc["content"] for doc in relevant_docs],
                answer=answer,
                sources=sources,
                rating=rating,
                metadata={
                    "llm_provider": self.llm_provider,
                    "num_sources": len(sources),
                    "k": k,
                },
            )

        return result

    def get_stats(self) -> Dict:
        """Get statistics about the RAG system."""
        return {
            "vector_store": self.vector_store.get_collection_stats(),
            "llm_provider": self.llm_provider,
            "llm_configured": self.llm is not None,
        }

    def _generate_document_id(self, filename: str, content: str) -> str:
        """Generate a unique ID for a document based on filename and content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{filename}_{content_hash}"

    def ingest_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Ingest documents with proper metadata tracking.

        Args:
            documents: List of dicts with 'content' and 'metadata' keys

        Returns:
            List of ingestion results
        """
        results = []
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            filename = metadata.get("source", "unknown")

            doc_id = self._generate_document_id(filename, content)
            chunks = text_splitter.split_text(content)

            langchain_docs = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "source": filename,
                    "type": metadata.get("type", "unknown"),
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "ingestion_date": datetime.now().isoformat(),
                }
                chunk_metadata.update({k: v for k, v in metadata.items()
                                       if k not in ["source", "type"]})

                langchain_docs.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata,
                ))

            self.vector_store.add_documents(langchain_docs)

            results.append({
                "status": "success",
                "doc_id": doc_id,
                "filename": filename,
                "chunks_created": len(chunks),
            })

        return results

    def list_documents(self) -> List[Dict]:
        """List all documents in the database."""
        return self.vector_store.list_documents()

    def delete_document(self, doc_id: str) -> Dict[str, any]:
        """Delete a document by ID."""
        return self.vector_store.delete_document(doc_id)

    def update_document_folder(self, doc_id: str, new_folder: str) -> Dict[str, any]:
        """Update document folder."""
        return self.vector_store.update_document_folder(doc_id, new_folder)

    def search_documents(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search documents with optional metadata filter."""
        return self.vector_store.search_documents(query, k, filter_metadata)

    def _load_folders(self) -> List[str]:
        """Load folders from JSON file."""
        if os.path.exists(self.folders_file):
            try:
                with open(self.folders_file, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_folders(self, folders: List[str]):
        """Save folders to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.folders_file), exist_ok=True)
            with open(self.folders_file, "w") as f:
                json.dump(folders, f, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save folders: {str(e)}")

    def create_folder(self, folder_name: str) -> Dict[str, any]:
        """Create a new empty folder."""
        try:
            folder_name = folder_name.strip()
            if not folder_name:
                return {"status": "error", "error": "Folder name cannot be empty"}

            folders = self._load_folders()

            if folder_name in folders:
                return {"status": "error", "error": f"Folder '{folder_name}' already exists"}

            folders.append(folder_name)
            folders.sort()
            self._save_folders(folders)

            return {"status": "success", "folder_name": folder_name}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_all_folders(self) -> List[str]:
        """List all folders (both empty and those with documents)."""
        try:
            stored_folders = set(self._load_folders())
            results = self.vector_store.collection.get()
            doc_folders = set()

            for metadata in results.get("metadatas", []):
                folder = metadata.get("folder")
                if folder:
                    doc_folders.add(folder)

            return sorted(stored_folders | doc_folders)

        except Exception:
            return self._load_folders()

    def delete_folder(self, folder_name: str) -> Dict[str, any]:
        """Delete an empty folder."""
        try:
            results = self.vector_store.collection.get(where={"folder": folder_name})

            if results.get("ids"):
                return {
                    "status": "error",
                    "error": f"Cannot delete folder '{folder_name}' because it contains documents",
                }

            folders = self._load_folders()

            if folder_name not in folders:
                return {"status": "not_found", "folder_name": folder_name}

            folders.remove(folder_name)
            self._save_folders(folders)

            return {"status": "success", "folder_name": folder_name}

        except Exception as e:
            return {"status": "error", "error": str(e)}


class SimpleRAGSystem:
    """
    Simplified RAG system that doesn't require an LLM.
    Just retrieves relevant context from the vector store.
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        """Initialize simple RAG system."""
        self.vector_store = vector_store or VectorStore()
        self.document_processor = DocumentProcessor()

    def ingest_scraped_data(self, scraped_data: List[Dict]) -> None:
        """Ingest scraped data."""
        print("Processing scraped data...")
        documents = self.document_processor.prepare_documents_for_rag(scraped_data)
        self.vector_store.add_documents(documents)
        print("Successfully ingested data")

    def query(self, question: str, k: int = 4) -> Dict:
        """Query and return relevant context."""
        relevant_docs = self.vector_store.similarity_search(question, k=k)

        if not relevant_docs:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": [],
                "context": [],
            }

        context_pieces = []
        sources = []

        for i, doc in enumerate(relevant_docs):
            source_title = doc["metadata"].get("title", "Unknown")
            source_url = doc["metadata"].get("source", "Unknown")
            relevance = round((1 - doc["distance"]) * 100, 1) if doc["distance"] else None

            header = f"--- SOURCE {i+1} "
            if relevance:
                header += f"({relevance}% relevant) "
            header += "---"

            source_info = f"From: {source_title}\nURL: {source_url}\n"
            context_pieces.append(f"{header}\n{source_info}\n{doc['content']}")

            sources.append({
                "url": source_url,
                "title": source_title,
                "relevance_score": round(1 - doc["distance"], 3) if doc["distance"] else None,
                "content": doc["content"],
            })

        return {
            "answer": "\n\n".join(context_pieces),
            "sources": sources,
            "context": [doc["content"] for doc in relevant_docs],
        }

    def get_stats(self) -> Dict:
        """Get statistics."""
        return self.vector_store.get_collection_stats()
