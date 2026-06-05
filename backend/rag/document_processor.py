"""
Document processing utilities for splitting and preparing documents for RAG.
"""

from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentProcessor:
    """Process documents for RAG ingestion."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def process_scraped_data(self, scraped_data: List[Dict]) -> List[Document]:
        """
        Process scraped data into LangChain documents.

        Args:
            scraped_data: List of dictionaries from web scraper

        Returns:
            List of LangChain Document objects
        """
        documents = []

        for item in scraped_data:
            # Create a document for each scraped item
            doc = Document(
                page_content=item['content'],
                metadata={
                    'source': item['url'],
                    'title': item['title'],
                    'type': item['type']
                }
            )
            documents.append(doc)

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks.

        Args:
            documents: List of LangChain documents

        Returns:
            List of split documents
        """
        split_docs = self.text_splitter.split_documents(documents)
        print(f"Split {len(documents)} documents into {len(split_docs)} chunks")
        return split_docs

    def prepare_documents_for_rag(self, scraped_data: List[Dict]) -> List[Document]:
        """
        Complete pipeline to prepare scraped data for RAG.

        Args:
            scraped_data: List of dictionaries from web scraper

        Returns:
            List of split and processed documents ready for embedding
        """
        # Convert to documents
        documents = self.process_scraped_data(scraped_data)

        # Split into chunks
        split_docs = self.split_documents(documents)

        return split_docs
