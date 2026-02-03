import asyncio
import json
import uuid
from datetime import datetime, timezone
import structlog
import redis.asyncio as redis
import httpx
from sentence_transformers import SentenceTransformer

from config import settings
from models import (
    IndexJobStatus,
    DataSourceConfig,
    GitHubSourceConfig,
    JiraSourceConfig,
    ConfluenceSourceConfig,
    CodeChunk,
    DocumentChunk,
)
from indexers import GitHubIndexer, JiraIndexer, ConfluenceIndexer

logger = structlog.get_logger()

REDIS_JOB_QUEUE = "indexer:jobs"
REDIS_JOB_STATUS_PREFIX = "indexer:status:"


class IndexerWorker:
    def __init__(self):
        self.redis: redis.Redis | None = None
        self.embedding_model: SentenceTransformer | None = None
        self.running = False

    async def start(self):
        logger.info("indexer_worker_starting")

        self.redis = redis.from_url(settings.redis_url)
        self.embedding_model = SentenceTransformer(settings.embedding_model)

        self.running = True
        logger.info("indexer_worker_started")

        while self.running:
            try:
                job_data = await self.redis.brpop(REDIS_JOB_QUEUE, timeout=5)
                if job_data:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    await self.process_job(job)
            except Exception as e:
                logger.error("job_processing_error", error=str(e))
                await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("indexer_worker_stopped")

    async def process_job(self, job: dict):
        job_id = job.get("job_id", str(uuid.uuid4()))
        org_id = job.get("org_id")
        source_id = job.get("source_id")
        job_type = job.get("job_type", "incremental")

        logger.info("processing_job", job_id=job_id, org_id=org_id, source_id=source_id)

        status = IndexJobStatus(
            job_id=job_id,
            org_id=org_id,
            source_id=source_id,
            job_type=job_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        await self._update_status(status)

        try:
            sources = await self._fetch_sources(org_id, source_id)

            for source in sources:
                await self._index_source(source, status)

            status.status = "completed"
            status.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("job_failed", job_id=job_id, error=str(e))
            status.status = "failed"
            status.error_message = str(e)
            status.completed_at = datetime.now(timezone.utc)

        await self._update_status(status)
        await self._publish_completion(status)

    async def _fetch_sources(
        self, org_id: str, source_id: str | None
    ) -> list[DataSourceConfig]:
        async with httpx.AsyncClient() as client:
            url = f"http://dashboard-api:5000/api/sources/{org_id}"
            if source_id:
                url += f"/{source_id}"

            response = await client.get(url, timeout=30.0)

            if response.status_code == 404:
                return []

            if response.status_code != 200:
                raise Exception(f"Failed to fetch sources: {response.status_code}")

            data = response.json()

            if isinstance(data, list):
                return [self._parse_source_config(s) for s in data]
            return [self._parse_source_config(data)]

    def _parse_source_config(self, data: dict) -> DataSourceConfig:
        source_type = data.get("source_type")
        config_data = json.loads(data.get("config_json", "{}"))

        if source_type == "github":
            config = GitHubSourceConfig(**config_data)
        elif source_type == "jira":
            config = JiraSourceConfig(**config_data)
        elif source_type == "confluence":
            config = ConfluenceSourceConfig(**config_data)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        return DataSourceConfig(
            source_id=data.get("source_id"),
            org_id=data.get("org_id"),
            source_type=source_type,
            name=data.get("name"),
            enabled=data.get("enabled", True),
            config=config,
        )

    async def _index_source(self, source: DataSourceConfig, status: IndexJobStatus):
        if not source.enabled:
            logger.info("skipping_disabled_source", source_id=source.source_id)
            return

        logger.info(
            "indexing_source",
            source_id=source.source_id,
            source_type=source.source_type,
        )

        if source.source_type == "github":
            await self._index_github(source, status)
        elif source.source_type == "jira":
            await self._index_jira(source, status)
        elif source.source_type == "confluence":
            await self._index_confluence(source, status)

    async def _index_github(self, source: DataSourceConfig, status: IndexJobStatus):
        if not isinstance(source.config, GitHubSourceConfig):
            return

        indexer = GitHubIndexer(source.org_id, source.config)

        repos = await indexer.fetch_matching_repos()
        status.items_total += len(repos)
        await self._update_status(status)

        all_chunks: list[CodeChunk] = []

        for repo in repos:
            try:
                repo_url = repo.get("clone_url", repo.get("html_url", ""))
                repo_name = repo.get("full_name", repo.get("name", ""))

                repo_path = await indexer.clone_or_pull_repo(
                    repo_url, repo_name.replace("/", "_")
                )

                chunks = await indexer.index_repo(repo_path, repo_name)
                all_chunks.extend(chunks)

                await self._index_to_gkg(source.org_id, str(repo_path))

                status.items_processed += 1
                status.progress_percent = int(
                    (status.items_processed / status.items_total) * 100
                )
                await self._update_status(status)

            except Exception as e:
                logger.error(
                    "repo_indexing_failed", repo=repo.get("name"), error=str(e)
                )
                status.items_failed += 1

        await self._store_code_chunks(source.org_id, all_chunks)

    async def _index_jira(self, source: DataSourceConfig, status: IndexJobStatus):
        if not isinstance(source.config, JiraSourceConfig):
            return

        indexer = JiraIndexer(source.org_id, source.config)

        tickets = await indexer.fetch_tickets()
        status.items_total += len(tickets)
        await self._update_status(status)

        chunks = await indexer.index_tickets(tickets)
        status.items_processed = len(chunks)
        status.progress_percent = 100
        await self._update_status(status)

        await self._store_document_chunks(source.org_id, chunks, "jira_tickets")

    async def _index_confluence(self, source: DataSourceConfig, status: IndexJobStatus):
        if not isinstance(source.config, ConfluenceSourceConfig):
            return

        indexer = ConfluenceIndexer(source.org_id, source.config)

        pages = await indexer.fetch_pages()
        status.items_total += len(pages)
        await self._update_status(status)

        chunks = await indexer.index_pages(pages)
        status.items_processed = len(chunks)
        status.progress_percent = 100
        await self._update_status(status)

        await self._store_document_chunks(source.org_id, chunks, "confluence_docs")

    async def _store_code_chunks(self, org_id: str, chunks: list[CodeChunk]):
        if not chunks or not self.embedding_model:
            return

        logger.info("storing_code_chunks", count=len(chunks), org_id=org_id)

        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            ids = [c.id for c in batch]
            documents = [c.content for c in batch]
            metadatas = [
                {
                    "org_id": org_id,
                    "repo": c.repo,
                    "file_path": c.file_path,
                    "language": c.language,
                    "chunk_type": c.chunk_type,
                    "name": c.name or "",
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                }
                for c in batch
            ]

            embeddings = self.embedding_model.encode(documents).tolist()

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.chromadb_url}/api/v1/collections/code/upsert",
                    json={
                        "ids": ids,
                        "documents": documents,
                        "metadatas": metadatas,
                        "embeddings": embeddings,
                    },
                    timeout=60.0,
                )

        logger.info("code_chunks_stored", count=len(chunks))

    async def _store_document_chunks(
        self, org_id: str, chunks: list[DocumentChunk], collection: str
    ):
        if not chunks or not self.embedding_model:
            return

        logger.info("storing_document_chunks", count=len(chunks), collection=collection)

        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            ids = [c.id for c in batch]
            documents = [c.content for c in batch]
            metadatas = [
                {
                    "org_id": org_id,
                    **{
                        k: (json.dumps(v) if isinstance(v, list) else v)
                        for k, v in c.metadata.items()
                    },
                }
                for c in batch
            ]

            embeddings = self.embedding_model.encode(documents).tolist()

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.chromadb_url}/api/v1/collections/{collection}/upsert",
                    json={
                        "ids": ids,
                        "documents": documents,
                        "metadatas": metadatas,
                        "embeddings": embeddings,
                    },
                    timeout=60.0,
                )

        logger.info("document_chunks_stored", count=len(chunks), collection=collection)

    async def _index_to_gkg(self, org_id: str, repo_path: str):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.gkg_url}/index",
                    json={"org_id": org_id, "repo_path": repo_path},
                    timeout=300.0,
                )
        except Exception as e:
            logger.warning("gkg_indexing_failed", repo_path=repo_path, error=str(e))

    async def _update_status(self, status: IndexJobStatus):
        if self.redis:
            key = f"{REDIS_JOB_STATUS_PREFIX}{status.job_id}"
            await self.redis.setex(key, 3600, status.model_dump_json())

    async def _publish_completion(self, status: IndexJobStatus):
        if self.redis:
            await self.redis.publish(
                f"indexer:completed:{status.org_id}",
                status.model_dump_json(),
            )


async def main():
    worker = IndexerWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
