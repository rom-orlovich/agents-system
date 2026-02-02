import os
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings


class ChromaDBClient:
    def __init__(self) -> None:
        self._client: chromadb.HttpClient | None = None

    @property
    def client(self) -> chromadb.HttpClient:
        if self._client is None:
            host = os.getenv("CHROMA_HOST", "chromadb")
            port = int(os.getenv("CHROMA_PORT", "8000"))
            self._client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    def get_collection(self, name: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def store_document(
        self,
        content: str,
        metadata: dict[str, Any],
        collection_name: str = "default",
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        collection = self.get_collection(collection_name)
        doc_id = doc_id or str(uuid.uuid4())

        collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )

        return {
            "success": True,
            "id": doc_id,
            "collection": collection_name,
            "message": f"Document stored successfully in {collection_name}",
        }

    async def query_documents(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str = "default",
        filter_metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        collection = self.get_collection(collection_name)

        where_filter = filter_metadata if filter_metadata else None

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "id": doc_id,
                        "content": results["documents"][0][i]
                        if results["documents"]
                        else "",
                        "metadata": results["metadatas"][0][i]
                        if results["metadatas"]
                        else {},
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else 0.0,
                        "collection": collection_name,
                    }
                )

        return {
            "results": formatted_results,
            "query": query,
            "collection": collection_name,
            "count": len(formatted_results),
        }

    async def list_collections(self) -> dict[str, Any]:
        collections = self.client.list_collections()
        return {
            "collections": [{"name": c.name, "count": c.count()} for c in collections],
            "action": "list",
            "message": f"Found {len(collections)} collections",
        }

    async def create_collection(self, name: str) -> dict[str, Any]:
        self.client.get_or_create_collection(name=name)
        return {
            "collections": [{"name": name, "count": 0}],
            "action": "create",
            "message": f"Collection '{name}' created successfully",
        }

    async def delete_collection(self, name: str) -> dict[str, Any]:
        self.client.delete_collection(name=name)
        return {
            "collections": [],
            "action": "delete",
            "message": f"Collection '{name}' deleted successfully",
        }

    async def update_document(
        self,
        doc_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        collection_name: str = "default",
    ) -> dict[str, Any]:
        collection = self.get_collection(collection_name)

        update_args: dict[str, Any] = {"ids": [doc_id]}
        if content:
            update_args["documents"] = [content]
        if metadata:
            update_args["metadatas"] = [metadata]

        collection.update(**update_args)

        return {
            "success": True,
            "id": doc_id,
            "collection": collection_name,
            "message": f"Document {doc_id} updated successfully",
        }

    async def delete_document(
        self,
        doc_id: str,
        collection_name: str = "default",
    ) -> dict[str, Any]:
        collection = self.get_collection(collection_name)
        collection.delete(ids=[doc_id])

        return {
            "success": True,
            "id": doc_id,
            "collection": collection_name,
            "message": f"Document {doc_id} deleted successfully",
        }


chroma_client = ChromaDBClient()
