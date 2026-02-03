from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from .models import Base


def utc_now():
    return datetime.now(timezone.utc)


class OrganizationDB(Base):
    __tablename__ = "organizations"

    org_id = Column(String(255), primary_key=True)
    name = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    settings_json = Column(Text, default="{}", nullable=False)

    data_sources = relationship(
        "DataSourceDB", back_populates="organization", cascade="all, delete-orphan"
    )
    indexing_jobs = relationship(
        "IndexingJobDB", back_populates="organization", cascade="all, delete-orphan"
    )


class DataSourceDB(Base):
    __tablename__ = "data_sources"

    source_id = Column(String(255), primary_key=True)
    org_id = Column(
        String(255),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    config_json = Column(Text, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_stats_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "org_id", "source_type", "name", name="uq_data_source_org_type_name"
        ),
        Index("idx_data_sources_org", "org_id"),
        Index("idx_data_sources_type", "source_type"),
    )

    organization = relationship("OrganizationDB", back_populates="data_sources")
    indexed_items = relationship(
        "IndexedItemDB", back_populates="data_source", cascade="all, delete-orphan"
    )


class IndexingJobDB(Base):
    __tablename__ = "indexing_jobs"

    job_id = Column(String(255), primary_key=True)
    org_id = Column(
        String(255),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id = Column(
        String(255),
        ForeignKey("data_sources.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    progress_percent = Column(Integer, default=0, nullable=False)
    items_total = Column(Integer, default=0, nullable=False)
    items_processed = Column(Integer, default=0, nullable=False)
    items_failed = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    __table_args__ = (
        Index("idx_indexing_jobs_org", "org_id"),
        Index("idx_indexing_jobs_status", "status"),
    )

    organization = relationship("OrganizationDB", back_populates="indexing_jobs")


class IndexedItemDB(Base):
    __tablename__ = "indexed_items"

    item_id = Column(String(255), primary_key=True)
    org_id = Column(String(255), nullable=False)
    source_id = Column(
        String(255),
        ForeignKey("data_sources.source_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(50), nullable=False)
    external_id = Column(String(500), nullable=False)
    collection = Column(String(100), nullable=False)
    chunk_count = Column(Integer, default=1, nullable=False)
    last_indexed_at = Column(DateTime, nullable=False)
    content_hash = Column(String(64), nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "org_id", "source_type", "external_id", name="uq_indexed_item_org_type_ext"
        ),
        Index("idx_indexed_items_org", "org_id"),
        Index("idx_indexed_items_source", "source_id"),
    )

    data_source = relationship("DataSourceDB", back_populates="indexed_items")
