import chromadb
from chromadb.config import Settings as ChromaSettings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from models import CollectionInfo

logger = structlog.get_logger()

COLLECTIONS = ["code", "jira_tickets", "confluence_docs", "github_issues"]


class ChromaClientManager:
    def __init__(self, chromadb_url: str):
        self.chromadb_url = chromadb_url
        self.client: chromadb.HttpClient | None = None
        self.collections: dict[str, chromadb.Collection] = {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    async def initialize(self):
        logger.info("chromadb_client_initializing", url=self.chromadb_url)

        host = self.chromadb_url.replace("http://", "").replace("https://", "")
        if ":" in host:
            host, port_str = host.split(":")
            port = int(port_str)
        else:
            port = 8000

        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        for collection_name in COLLECTIONS:
            try:
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self.collections[collection_name] = collection
                logger.info(
                    "chromadb_collection_ready",
                    collection=collection_name,
                    count=collection.count(),
                )
            except Exception as e:
                logger.error(
                    "chromadb_collection_error",
                    collection=collection_name,
                    error=str(e),
                )

        logger.info(
            "chromadb_client_initialized", collections=list(self.collections.keys())
        )

    def get_collection(self, name: str) -> chromadb.Collection:
        if name not in self.collections:
            raise ValueError(f"Collection {name} not found")
        return self.collections[name]

    async def list_collections(self) -> list[str]:
        return list(self.collections.keys())

    async def get_collection_info(self) -> list[CollectionInfo]:
        info_list = []
        for name, collection in self.collections.items():
            info_list.append(
                CollectionInfo(
                    name=name,
                    count=collection.count(),
                    metadata=collection.metadata or {},
                )
            )
        return info_list

    async def query_collection(
        self,
        collection_name: str,
        query_texts: list[str],
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict:
        collection = self.get_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]] | None = None,
    ):
        collection = self.get_collection(collection_name)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info(
            "chromadb_documents_added",
            collection=collection_name,
            count=len(ids),
        )

    async def upsert_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]] | None = None,
    ):
        collection = self.get_collection(collection_name)
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info(
            "chromadb_documents_upserted",
            collection=collection_name,
            count=len(ids),
        )

    async def delete_documents(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        where: dict | None = None,
    ):
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids, where=where)
        logger.info(
            "chromadb_documents_deleted",
            collection=collection_name,
            ids_count=len(ids) if ids else 0,
        )
