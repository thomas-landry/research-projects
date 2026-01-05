#!/usr/bin/env python3
"""
ChromaDB Vector Storage for semantic search across extracted documents.

Stores document chunks with embeddings for RAG and semantic retrieval.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import chromadb
from chromadb.utils import embedding_functions


def _sanitize_metadata_value(value: Any) -> Any:
    """Sanitize a value for safe storage in ChromaDB metadata."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        # Limit string length and remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(value))
        return sanitized[:1000]  # Limit to 1000 chars
    if isinstance(value, (list, dict)):
        # Convert to string with length limit
        return str(value)[:1000]
    return str(value)[:1000]


def load_env():
    """Load environment from .env file."""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent / ".env",
        Path.home() / "Projects" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            break


@dataclass
class VectorDocument:
    """Document to store in vector database."""
    id: str
    text: str
    metadata: Dict[str, Any]


class ChromaVectorStore:
    """ChromaDB-based vector storage for document chunks."""
    
    def __init__(
        self,
        collection_name: str = "systematic_review",
        persist_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist data (None for in-memory)
            embedding_model: Sentence-transformers model for embeddings
        """
        load_env()
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        
        self._client = None
        self._collection = None
        self._embedding_fn = None
    
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB."""
        if self._client is not None:
            return
        
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Run: pip install chromadb"
            )
        
        # Initialize client
        if self.persist_directory:
            persist_path = Path(self.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_path))
        else:
            self._client = chromadb.Client()
        
        # Use sentence-transformers for embeddings (local, no API needed)
        try:
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
        except Exception:
            # Fallback to default embeddings
            self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def add_documents(
        self,
        documents: List[VectorDocument],
    ) -> int:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of VectorDocument objects
            
        Returns:
            Number of documents added
        """
        self._ensure_initialized()
        
        if not documents:
            return 0
        
        ids = [doc.id for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # ChromaDB handles embedding automatically
        self._collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )
        
        return len(documents)
    




    def add_chunks_from_parsed_doc(
        self,
        doc,  # ParsedDocument
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add chunks from a parsed document with optional extracted metadata.
        
        Args:
            doc: ParsedDocument object
            extracted_data: Optional dict of extracted fields to attach as metadata
            
        Returns:
            Number of chunks added
        """
        documents = []
        
        for i, chunk in enumerate(doc.chunks):
            # Build metadata
            metadata = {
                "filename": doc.filename,
                "section": chunk.section,
                "subsection": chunk.subsection,
                "chunk_type": chunk.chunk_type,
                "chunk_index": i,
            }
            
            # Add extracted data to metadata (for filtering)
            if extracted_data:
                for key, value in extracted_data.items():
                    # Skip internal fields and quote fields
                    if key.startswith("_") or key.endswith("_quote"):
                        continue
                    
                    sanitized = _sanitize_metadata_value(value)
                    if sanitized is not None:
                        metadata[key] = sanitized
            
            doc_id = f"{doc.filename}_{i}"
            
            documents.append(VectorDocument(
                id=doc_id,
                text=chunk.text,
                metadata=metadata,
            ))
        
        return self.add_documents(documents)
    
    def query(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
            where: Metadata filter (e.g., {"filename": "paper.pdf"})
            where_document: Document text filter
            
        Returns:
            List of matching documents with scores
        """
        self._ensure_initialized()
        
        kwargs = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document
        
        results = self._collection.query(**kwargs)
        
        # Format results
        formatted = []
        if results:
            ids = results.get('ids', [[]])[0]
            docs = results.get('documents', [[]])[0]
            metas = results.get('metadatas', [[]])[0]
            dists = results.get('distances', [[]])[0]
            
            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i] if i < len(ids) else None,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else None,
                })
        
        return formatted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        self._ensure_initialized()
        
        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_directory": self.persist_directory,
        }
    
    def delete_collection(self):
        """Delete the entire collection."""
        self._ensure_initialized()
        self._client.delete_collection(self.collection_name)
        self._collection = None


if __name__ == "__main__":
    # Quick test
    store = ChromaVectorStore(
        collection_name="test_sr",
        persist_directory="./output/test_vectors"
    )
    
    # Add test documents
    docs = [
        VectorDocument(
            id="doc1",
            text="Diffuse pulmonary meningotheliomatosis is a rare condition.",
            metadata={"filename": "test1.pdf", "section": "Abstract"}
        ),
        VectorDocument(
            id="doc2", 
            text="The patient presented with dyspnea and ground-glass opacities on CT.",
            metadata={"filename": "test1.pdf", "section": "Results"}
        ),
    ]
    
    added = store.add_documents(docs)
    print(f"Added {added} documents")
    
    # Query
    results = store.query("pulmonary nodules", n_results=2)
    print(f"\nQuery results: {len(results)}")
    for r in results:
        print(f"  - {r['text'][:50]}... (distance: {r['distance']:.3f})")
    
    print(f"\nStats: {store.get_stats()}")
