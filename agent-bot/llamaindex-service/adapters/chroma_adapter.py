import chromadb
from chromadb.config import Settings as ChromaSettings
import structlog

from core.models import SearchResult

logger = structlog.get_logger()


class ChromaVectorStore:
    """ChromaDB implementation of VectorStoreProtocol."""

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._client: chromadb.HttpClient | None = None
        self._collections: dict[str, chromadb.Collection] = {}

    async def initialize(self) -> None:
        """Initialize connection to ChromaDB."""
        logger.info("chroma_initializing", host=self._host, port=self._port)

        self._client = chromadb.HttpClient(
            host=self._host,
            port=self._port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        collection_names = ["code", "jira_tickets", "confluence_docs", "github_issues"]
        for name in collection_names:
            try:
                collection = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._collections[name] = collection
                logger.info("chroma_collection_ready", collection=name)
            except Exception as e:
                logger.error("chroma_collection_error", collection=name, error=str(e))

        logger.info("chroma_initialized")

    async def query(
        self,
        query_text: str,
        collection: str,
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[SearchResult]:
        """Query vectors by semantic similarity."""
        if collection not in self._collections:
            logger.warning("collection_not_found", collection=collection)
            return []

        coll = self._collections[collection]

        where_filter = None
        if filters:
            if len(filters) == 1:
                key, value = list(filters.items())[0]
                where_filter = {key: value}
            else:
                where_filter = {"$and": [{k: v} for k, v in filters.items()]}

        try:
            result = coll.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("chroma_query_error", collection=collection, error=str(e))
            return []

        return self._format_results(result, collection)

    def _format_results(self, result: dict, collection: str) -> list[SearchResult]:
        """Format ChromaDB results to SearchResult models."""
        results = []

        if not result.get("ids") or not result["ids"][0]:
            return results

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        source_type_map = {
            "code": "code",
            "jira_tickets": "jira",
            "confluence_docs": "confluence",
            "github_issues": "github_issues",
        }
        source_type = source_type_map.get(collection, "code")

        for i, doc in enumerate(documents):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            relevance_score = max(0.0, 1.0 - distance)

            source_id = self._extract_source_id(metadata, source_type)

            results.append(
                SearchResult(
                    content=doc,
                    source_type=source_type,
                    source_id=source_id,
                    relevance_score=relevance_score,
                    metadata=metadata,
                )
            )

        return results

    def _extract_source_id(self, metadata: dict, source_type: str) -> str:
        """Extract source ID from metadata."""
        if source_type == "code":
            repo = metadata.get("repo", "unknown")
            file_path = metadata.get("file_path", "unknown")
            return f"{repo}/{file_path}"
        elif source_type == "jira":
            return str(metadata.get("key", metadata.get("issue_key", "unknown")))
        elif source_type == "confluence":
            space = metadata.get("space", "unknown")
            title = metadata.get("page_title", "unknown")
            return f"{space}/{title}"
        return str(metadata.get("id", "unknown"))

    async def list_collections(self) -> list[str]:
        """List available collections."""
        return list(self._collections.keys())

    async def health_check(self) -> bool:
        """Check if ChromaDB is healthy."""
        try:
            if self._client:
                self._client.heartbeat()
                return True
            return False
        except Exception:
            return False
