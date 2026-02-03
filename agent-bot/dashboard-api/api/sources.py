import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.knowledge_models import (
    OrganizationDB,
    DataSourceDB,
    IndexingJobDB,
)


router = APIRouter(prefix="/api/sources", tags=["sources"])


class GitHubSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    include_patterns: list[str] = []
    exclude_patterns: list[str] = []
    topics: list[str] = []
    languages: list[str] = []
    branches: list[str] = ["main", "master"]
    file_patterns: list[str] = ["**/*.py", "**/*.ts", "**/*.js", "**/*.go"]
    exclude_file_patterns: list[str] = ["**/node_modules/**", "**/__pycache__/**"]


class JiraSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    jql: str = ""
    issue_types: list[str] = ["Bug", "Story", "Task"]
    include_labels: list[str] = []
    exclude_labels: list[str] = []
    max_results: int = 1000


class ConfluenceSourceConfig(BaseModel):
    model_config = ConfigDict(strict=True)

    spaces: list[str] = []
    include_labels: list[str] = []
    exclude_labels: list[str] = []
    content_types: list[str] = ["page", "blogpost"]


class CreateDataSourceRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    source_type: str
    config: dict
    enabled: bool = True


class UpdateDataSourceRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str | None = None
    config: dict | None = None
    enabled: bool | None = None


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    source_id: str
    org_id: str
    source_type: str
    name: str
    enabled: bool
    config_json: str
    last_sync_at: datetime | None
    last_sync_status: str | None
    created_at: datetime
    updated_at: datetime


class TriggerSyncRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    source_id: str | None = None
    job_type: str = "incremental"


class IndexingJobResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: str
    org_id: str
    source_id: str | None
    job_type: str
    status: str
    progress_percent: int
    items_total: int
    items_processed: int
    items_failed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


async def get_db_session():
    from core.database.session import async_session_maker

    async with async_session_maker() as session:
        yield session


@router.get("/{org_id}", response_model=list[DataSourceResponse])
async def list_data_sources(
    org_id: str,
    source_type: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    query = select(DataSourceDB).where(DataSourceDB.org_id == org_id)
    if source_type:
        query = query.where(DataSourceDB.source_type == source_type)

    result = await db.execute(query)
    sources = result.scalars().all()

    return [
        DataSourceResponse(
            source_id=s.source_id,
            org_id=s.org_id,
            source_type=s.source_type,
            name=s.name,
            enabled=s.enabled,
            config_json=s.config_json,
            last_sync_at=s.last_sync_at,
            last_sync_status=s.last_sync_status,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sources
    ]


@router.get("/{org_id}/{source_id}", response_model=DataSourceResponse)
async def get_data_source(
    org_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(DataSourceDB).where(
            DataSourceDB.org_id == org_id,
            DataSourceDB.source_id == source_id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    return DataSourceResponse(
        source_id=source.source_id,
        org_id=source.org_id,
        source_type=source.source_type,
        name=source.name,
        enabled=source.enabled,
        config_json=source.config_json,
        last_sync_at=source.last_sync_at,
        last_sync_status=source.last_sync_status,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.post("/{org_id}", response_model=DataSourceResponse)
async def create_data_source(
    org_id: str,
    request: CreateDataSourceRequest,
    db: AsyncSession = Depends(get_db_session),
):
    org_result = await db.execute(
        select(OrganizationDB).where(OrganizationDB.org_id == org_id)
    )
    org = org_result.scalar_one_or_none()

    if not org:
        org = OrganizationDB(org_id=org_id, name=org_id)
        db.add(org)

    source_id = str(uuid.uuid4())
    source = DataSourceDB(
        source_id=source_id,
        org_id=org_id,
        source_type=request.source_type,
        name=request.name,
        enabled=request.enabled,
        config_json=json.dumps(request.config),
        created_by="system",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    return DataSourceResponse(
        source_id=source.source_id,
        org_id=source.org_id,
        source_type=source.source_type,
        name=source.name,
        enabled=source.enabled,
        config_json=source.config_json,
        last_sync_at=source.last_sync_at,
        last_sync_status=source.last_sync_status,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.patch("/{org_id}/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    org_id: str,
    source_id: str,
    request: UpdateDataSourceRequest,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(DataSourceDB).where(
            DataSourceDB.org_id == org_id,
            DataSourceDB.source_id == source_id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    if request.name is not None:
        source.name = request.name
    if request.config is not None:
        source.config_json = json.dumps(request.config)
    if request.enabled is not None:
        source.enabled = request.enabled

    source.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(source)

    return DataSourceResponse(
        source_id=source.source_id,
        org_id=source.org_id,
        source_type=source.source_type,
        name=source.name,
        enabled=source.enabled,
        config_json=source.config_json,
        last_sync_at=source.last_sync_at,
        last_sync_status=source.last_sync_status,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.delete("/{org_id}/{source_id}")
async def delete_data_source(
    org_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(DataSourceDB).where(
            DataSourceDB.org_id == org_id,
            DataSourceDB.source_id == source_id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    await db.delete(source)
    await db.commit()

    return {"status": "deleted", "source_id": source_id}


@router.post("/{org_id}/sync", response_model=IndexingJobResponse)
async def trigger_sync(
    org_id: str,
    request: TriggerSyncRequest,
    db: AsyncSession = Depends(get_db_session),
):
    job_id = str(uuid.uuid4())
    job = IndexingJobDB(
        job_id=job_id,
        org_id=org_id,
        source_id=request.source_id,
        job_type=request.job_type,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    import redis.asyncio as redis

    redis_client = redis.from_url("redis://redis:6379/0")
    await redis_client.lpush(
        "indexer:jobs",
        json.dumps({
            "job_id": job_id,
            "org_id": org_id,
            "source_id": request.source_id,
            "job_type": request.job_type,
        }),
    )
    await redis_client.close()

    return IndexingJobResponse(
        job_id=job.job_id,
        org_id=job.org_id,
        source_id=job.source_id,
        job_type=job.job_type,
        status=job.status,
        progress_percent=job.progress_percent,
        items_total=job.items_total,
        items_processed=job.items_processed,
        items_failed=job.items_failed,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@router.get("/{org_id}/jobs", response_model=list[IndexingJobResponse])
async def list_indexing_jobs(
    org_id: str,
    status: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session),
):
    query = (
        select(IndexingJobDB)
        .where(IndexingJobDB.org_id == org_id)
        .order_by(IndexingJobDB.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(IndexingJobDB.status == status)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        IndexingJobResponse(
            job_id=j.job_id,
            org_id=j.org_id,
            source_id=j.source_id,
            job_type=j.job_type,
            status=j.status,
            progress_percent=j.progress_percent,
            items_total=j.items_total,
            items_processed=j.items_processed,
            items_failed=j.items_failed,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get("/{org_id}/jobs/{job_id}", response_model=IndexingJobResponse)
async def get_indexing_job(
    org_id: str,
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(IndexingJobDB).where(
            IndexingJobDB.org_id == org_id,
            IndexingJobDB.job_id == job_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Indexing job not found")

    return IndexingJobResponse(
        job_id=job.job_id,
        org_id=job.org_id,
        source_id=job.source_id,
        job_type=job.job_type,
        status=job.status,
        progress_percent=job.progress_percent,
        items_total=job.items_total,
        items_processed=job.items_processed,
        items_failed=job.items_failed,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )
