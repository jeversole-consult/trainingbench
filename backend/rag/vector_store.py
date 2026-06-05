"""
Vector store using ChromaDB for RAG.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from langchain_core.documents import Document
from .embeddings import EmbeddingModel
import os


# Tunable defaults (env-overridable). Constructor arguments still win.
DEFAULT_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "documents")
DEFAULT_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
# ChromaDB caps a single `add()` call at ~5,461 records. Stay safely below.
CHROMA_ADD_BATCH = int(os.getenv("CHROMA_ADD_BATCH", "5000"))


class VectorStore:
    """Vector store for storing and retrieving document embeddings."""

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_directory: str = DEFAULT_PERSIST_DIRECTORY,
        embedding_model: Optional[EmbeddingModel] = None
    ):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist the database
            embedding_model: Custom embedding model (if None, creates default)
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # Initialize ChromaDB client
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Initialize embedding model
        self.embedding_model = embedding_model or EmbeddingModel()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        print(f"Vector store initialized with collection: {collection_name}")
        print(f"Current document count: {self.collection.count()}")

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of LangChain documents to add
        """
        if not documents:
            print("No documents to add")
            return

        print(f"Adding {len(documents)} documents to vector store...")

        # Extract texts and metadata
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        # Generate embeddings (single call — embed_texts handles its own batching)
        print("Generating embeddings...")
        embeddings = self.embedding_model.embed_texts(texts)

        # Generate IDs
        existing_count = self.collection.count()
        ids = [f"doc_{existing_count + i}" for i in range(len(documents))]

        # Add to collection in batches to stay under ChromaDB's per-call cap
        total = len(documents)
        for start in range(0, total, CHROMA_ADD_BATCH):
            end = min(start + CHROMA_ADD_BATCH, total)
            print(f"  writing batch {start}-{end} of {total}...")
            self.collection.add(
                embeddings=embeddings[start:end],
                documents=texts[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end]
            )

        print(f"Successfully added {total} documents")
        print(f"Total documents in store: {self.collection.count()}")

    def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> List[Dict]:
        """
        Search for similar documents.

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of dictionaries containing documents and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.embed_text(query)

        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })

        return formatted_results

    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        # Delete and recreate collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Cleared collection: {self.collection_name}")

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        return {
            'name': self.collection_name,
            'count': self.collection.count(),
            'persist_directory': self.persist_directory
        }

    def list_documents(self) -> List[Dict]:
        """
        List all unique documents in the database.

        Returns:
            List of documents with their metadata
        """
        try:
            # Get total count and fetch all documents
            total_count = self.collection.count()

            # Fetch all documents with explicit limit (ChromaDB max is 100k, but we set higher for safety)
            results = self.collection.get(limit=max(total_count, 100000))

            # Extract unique documents by doc_id
            unique_docs = {}
            for metadata in results.get('metadatas', []):
                doc_id = metadata.get('doc_id')
                if doc_id and doc_id not in unique_docs:
                    unique_docs[doc_id] = {
                        "doc_id": doc_id,
                        "filename": metadata.get('source'),
                        "type": metadata.get('type'),
                        "ingestion_date": metadata.get('ingestion_date'),
                        "total_chunks": metadata.get('total_chunks', 0),
                        "folder": metadata.get('folder', '')
                    }

            return list(unique_docs.values())

        except Exception as e:
            raise ValueError(f"Failed to list documents: {str(e)}")

    def delete_document(self, doc_id: str) -> Dict[str, any]:
        """
        Delete a document and all its chunks from the database.

        Args:
            doc_id: ID of the document to delete

        Returns:
            Dictionary containing deletion status
        """
        try:
            # Get all IDs with matching doc_id
            results = self.collection.get(where={"doc_id": doc_id})
            ids_to_delete = results.get('ids', [])

            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)

                return {
                    "status": "success",
                    "doc_id": doc_id,
                    "chunks_deleted": len(ids_to_delete)
                }
            else:
                return {
                    "status": "not_found",
                    "doc_id": doc_id
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "doc_id": doc_id
            }

    def update_document_folder(self, doc_id: str, new_folder: str) -> Dict[str, any]:
        """
        Update the folder metadata for all chunks of a document.

        Args:
            doc_id: ID of the document to update
            new_folder: New folder name (empty string to remove folder)

        Returns:
            Dictionary containing update status
        """
        try:
            # Get all chunks with matching doc_id
            results = self.collection.get(where={"doc_id": doc_id})
            ids = results.get('ids', [])
            metadatas = results.get('metadatas', [])

            if not ids:
                return {
                    "status": "not_found",
                    "doc_id": doc_id
                }

            # Update metadata for each chunk
            updated_metadatas = []
            for metadata in metadatas:
                updated_metadata = metadata.copy()
                if new_folder:
                    updated_metadata['folder'] = new_folder
                elif 'folder' in updated_metadata:
                    # Remove folder key if new_folder is empty
                    del updated_metadata['folder']
                updated_metadatas.append(updated_metadata)

            # Update all chunks with new metadata
            self.collection.update(
                ids=ids,
                metadatas=updated_metadatas
            )

            return {
                "status": "success",
                "doc_id": doc_id,
                "chunks_updated": len(ids),
                "new_folder": new_folder if new_folder else None
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "doc_id": doc_id
            }

    def search_documents(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant document chunks based on a query.

        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of relevant document chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.embed_text(query)

            # Perform similarity search with optional filter
            if filter_metadata:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=filter_metadata
                )
            else:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k
                )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })

            return formatted_results

        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}")
