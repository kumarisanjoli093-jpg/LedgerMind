
import json
import math
import os
import sqlite3
import hashlib

from pathlib import Path
from typing import Optional

from .gemini_client import get_gemini_client


EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001"
)

DEFAULT_DB_PATH = os.getenv(
    "LEDGERMIND_RAG_DB",
    "data/ledgermind_rag.sqlite3"
)

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
EMBEDDING_BATCH_SIZE = 50


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.

    Stores document chunks and their Gemini embeddings in SQLite.
    Retrieves relevant chunks using cosine similarity.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH

        Path(self.db_path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_document_id
                ON document_chunks(document_id)
            """)

    @staticmethod
    def _chunk_text(text: str):
        """Split long documents into overlapping chunks."""

        text = text.strip()

        if not text:
            raise ValueError("Document text cannot be empty.")

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))

            if end < len(text):
                boundary = text.rfind(" ", start, end)

                if boundary > start:
                    end = boundary

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = end - CHUNK_OVERLAP

        return chunks

    @staticmethod
    def _embed_texts(texts, task_type):
        """Generate Gemini embeddings in batches."""

        client = get_gemini_client()
        embeddings = []

        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[
                start:start + EMBEDDING_BATCH_SIZE
            ]

            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config={
                    "task_type": task_type,
                    "output_dimensionality": 768
                }
            )

            if not response.embeddings:
                raise RuntimeError(
                    "Gemini returned no embeddings."
                )

            if len(response.embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding count does not match input count."
                )

            for item in response.embeddings:
                if not item.values:
                    raise RuntimeError(
                        "Gemini returned an empty embedding."
                    )

                vector = [float(value) for value in item.values]

                if not all(math.isfinite(value) for value in vector):
                    raise RuntimeError(
                        "Embedding contains invalid values."
                    )

                embeddings.append(vector)

        return embeddings

    def add_document(
        self,
        document_id: str,
        text: str,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Split, embed and store a document.

        Re-adding the same document_id replaces its old chunks.
        """

        if not document_id or not document_id.strip():
            raise ValueError("document_id is required.")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Valid document text is required.")

        metadata = metadata or {}

        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary.")

        chunks = self._chunk_text(text)

        vectors = self._embed_texts(
            chunks,
            "RETRIEVAL_DOCUMENT"
        )

        with self._connect() as connection:
            connection.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,)
            )

            for index, (chunk, vector) in enumerate(
                zip(chunks, vectors)
            ):
                chunk_id = hashlib.sha256(
                    f"{document_id}:{index}".encode()
                ).hexdigest()

                connection.execute("""
                    INSERT INTO document_chunks (
                        chunk_id,
                        document_id,
                        chunk_index,
                        content,
                        embedding,
                        metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id,
                    document_id,
                    index,
                    chunk,
                    json.dumps(vector),
                    json.dumps(metadata)
                ))

        return len(chunks)

    @staticmethod
    def _cosine_similarity(vector_a, vector_b):
        """Calculate cosine similarity between embeddings."""

        if len(vector_a) != len(vector_b):
            raise ValueError(
                "Embedding dimensions do not match."
            )

        dot_product = sum(
            a * b for a, b in zip(vector_a, vector_b)
        )

        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        vendor: Optional[str] = None,
        min_score: float = 0.0
    ) -> list[dict]:
        """
        Retrieve the most relevant document chunks.

        Optional vendor filtering uses metadata['vendor'].
        """

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20.")

        if not -1 <= min_score <= 1:
            raise ValueError("Invalid similarity threshold.")

        query_vector = self._embed_texts(
            [query],
            "RETRIEVAL_QUERY"
        )[0]

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM document_chunks"
            ).fetchall()

        results = []

        for row in rows:
            metadata = json.loads(row["metadata"])

            if vendor:
                stored_vendor = str(
                    metadata.get("vendor", "")
                ).strip().casefold()

                if stored_vendor != vendor.strip().casefold():
                    continue

            stored_vector = json.loads(row["embedding"])

            score = self._cosine_similarity(
                query_vector,
                stored_vector
            )

            if score < min_score:
                continue

            results.append({
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "metadata": metadata,
                "similarity": score
            })

        results.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        return results[:top_k]

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        vendor: Optional[str] = None
    ) -> str:
        """Return retrieved information as LLM-ready context."""

        results = self.retrieve(
            query=query,
            top_k=top_k,
            vendor=vendor
        )

        if not results:
            return "No relevant historical documents were found."

        context_parts = []

        for index, result in enumerate(results, start=1):
            context_parts.append(
                f"[Source {index}]\n"
                f"Document: {result['document_id']}\n"
                f"Vendor: {result['metadata'].get('vendor', 'Unknown')}\n"
                f"Similarity: {result['similarity']:.3f}\n"
                f"Content: {result['content']}"
            )

        return "\n\n".join(context_parts)

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document."""

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,)
            )

            return cursor.rowcount


# Reusable default RAG engine.
rag_engine = RAGEngine()

