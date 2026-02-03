import httpx
import structlog
from sentence_transformers import SentenceTransformer

from chroma_client import ChromaClientManager
from models import SearchResult

logger = structlog.get_logger()

SOURCE_TYPE_COLLECTION_MAP = {
    "code": "code",
    "jira": "jira_tickets",
    "confluence": "confluence_docs",
    "github_issues": "github_issues",
}


class HybridQueryEngine:
    def __init__(
        self,
        chroma_manager: ChromaClientManager,
        gkg_url: str,
        embedding_model: str,
    ):
        self.chroma_manager = chroma_manager
        self.gkg_url = gkg_url
        self.embedding_model_name = embedding_model
        self.embedding_model: SentenceTransformer | None = None

    async def _ensure_embedding_model(self):
        if self.embedding_model is None:
            logger.info("loading_embedding_model", model=self.embedding_model_name)
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("embedding_model_loaded")

    async def query(
        self,
        query: str,
        org_id: str,
        source_types: list[str],
        top_k: int = 10,
        include_metadata: bool = True,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []

        for source_type in source_types:
            collection_name = SOURCE_TYPE_COLLECTION_MAP.get(source_type)
            if not collection_name:
                continue

            try:
                source_results = await self._vector_search(
                    collection_name=collection_name,
                    query=query,
                    org_id=org_id,
                    top_k=top_k,
                    source_type=source_type,
                )
                results.extend(source_results)
            except Exception as e:
                logger.error(
                    "vector_search_failed",
                    collection=collection_name,
                    error=str(e),
                )

        if "code" in source_types and results:
            try:
                results = await self._enrich_with_graph_context(query, results, org_id)
            except Exception as e:
                logger.error("graph_enrichment_failed", error=str(e))

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    async def _vector_search(
        self,
        collection_name: str,
        query: str,
        org_id: str,
        top_k: int,
        source_type: str,
    ) -> list[SearchResult]:
        query_result = await self.chroma_manager.query_collection(
            collection_name=collection_name,
            query_texts=[query],
            n_results=top_k,
            where={"org_id": org_id},
        )

        results = []
        if query_result and query_result.get("documents"):
            documents = query_result["documents"][0]
            metadatas = (
                query_result["metadatas"][0] if query_result.get("metadatas") else []
            )
            distances = (
                query_result["distances"][0] if query_result.get("distances") else []
            )

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                relevance_score = 1.0 - distance

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
        if source_type == "code":
            repo = metadata.get("repo", "unknown")
            file_path = metadata.get("file_path", "unknown")
            return f"{repo}/{file_path}"
        elif source_type == "jira":
            return metadata.get("key", metadata.get("issue_key", "unknown"))
        elif source_type == "confluence":
            space = metadata.get("space", "unknown")
            title = metadata.get("page_title", "unknown")
            return f"{space}/{title}"
        return metadata.get("id", "unknown")

    async def _enrich_with_graph_context(
        self,
        query: str,
        results: list[SearchResult],
        org_id: str,
    ) -> list[SearchResult]:
        code_results = [r for r in results if r.source_type == "code"]
        if not code_results:
            return results

        entities = []
        for result in code_results[:5]:
            if result.metadata.get("name"):
                entities.append(
                    {
                        "name": result.metadata["name"],
                        "type": result.metadata.get("chunk_type", "function"),
                    }
                )

        if not entities:
            return results

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gkg_url}/graph/batch-related",
                    json={"entities": entities, "org_id": org_id, "depth": 1},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    graph_data = response.json()
                    for result in code_results:
                        entity_name = result.metadata.get("name")
                        if entity_name and entity_name in graph_data:
                            result.metadata["graph_context"] = graph_data[entity_name]
        except Exception as e:
            logger.warning("graph_enrichment_skipped", error=str(e))

        return results

    async def query_code(
        self,
        query: str,
        org_id: str,
        filters: dict[str, str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        where_filter: dict = {"org_id": org_id}

        if filters:
            if filters.get("repo") and filters["repo"] != "*":
                where_filter["repo"] = filters["repo"]
            if filters.get("language") and filters["language"] != "*":
                where_filter["language"] = filters["language"]

        query_result = await self.chroma_manager.query_collection(
            collection_name="code",
            query_texts=[query],
            n_results=top_k,
            where=where_filter if len(where_filter) > 1 else {"org_id": org_id},
        )

        results = []
        if query_result and query_result.get("documents"):
            documents = query_result["documents"][0]
            metadatas = (
                query_result["metadatas"][0] if query_result.get("metadatas") else []
            )
            distances = (
                query_result["distances"][0] if query_result.get("distances") else []
            )

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0

                results.append(
                    SearchResult(
                        content=doc,
                        source_type="code",
                        source_id=self._extract_source_id(metadata, "code"),
                        relevance_score=1.0 - distance,
                        metadata=metadata,
                    )
                )

        return results

    async def query_tickets(
        self,
        query: str,
        org_id: str,
        filters: dict[str, str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        where_filter: dict = {"org_id": org_id}

        if filters:
            if filters.get("project") and filters["project"] != "*":
                where_filter["project"] = filters["project"]
            if filters.get("status") and filters["status"] != "*":
                where_filter["status"] = filters["status"]

        query_result = await self.chroma_manager.query_collection(
            collection_name="jira_tickets",
            query_texts=[query],
            n_results=top_k,
            where=where_filter if len(where_filter) > 1 else {"org_id": org_id},
        )

        results = []
        if query_result and query_result.get("documents"):
            documents = query_result["documents"][0]
            metadatas = (
                query_result["metadatas"][0] if query_result.get("metadatas") else []
            )
            distances = (
                query_result["distances"][0] if query_result.get("distances") else []
            )

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0

                results.append(
                    SearchResult(
                        content=doc,
                        source_type="jira",
                        source_id=self._extract_source_id(metadata, "jira"),
                        relevance_score=1.0 - distance,
                        metadata=metadata,
                    )
                )

        return results

    async def query_docs(
        self,
        query: str,
        org_id: str,
        filters: dict[str, str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        where_filter: dict = {"org_id": org_id}

        if filters:
            if filters.get("space") and filters["space"] != "*":
                where_filter["space"] = filters["space"]

        query_result = await self.chroma_manager.query_collection(
            collection_name="confluence_docs",
            query_texts=[query],
            n_results=top_k,
            where=where_filter if len(where_filter) > 1 else {"org_id": org_id},
        )

        results = []
        if query_result and query_result.get("documents"):
            documents = query_result["documents"][0]
            metadatas = (
                query_result["metadatas"][0] if query_result.get("metadatas") else []
            )
            distances = (
                query_result["distances"][0] if query_result.get("distances") else []
            )

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0

                results.append(
                    SearchResult(
                        content=doc,
                        source_type="confluence",
                        source_id=self._extract_source_id(metadata, "confluence"),
                        relevance_score=1.0 - distance,
                        metadata=metadata,
                    )
                )

        return results

    async def get_related_entities(
        self,
        entity: str,
        entity_type: str,
        org_id: str,
        relationship: str = "all",
    ) -> dict[str, list[dict[str, str | int]]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gkg_url}/graph/related",
                    json={
                        "entity": entity,
                        "entity_type": entity_type,
                        "org_id": org_id,
                        "relationship": relationship,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json().get("relationships", {})
        except Exception as e:
            logger.error("get_related_entities_failed", entity=entity, error=str(e))
            return {}
