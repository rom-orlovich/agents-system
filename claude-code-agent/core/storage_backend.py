"""
Storage Backend Abstraction Layer
==================================

Supports multiple storage backends:
- Local filesystem (Docker with volumes)
- S3-compatible object storage (cloud deployment)
- PostgreSQL BLOB storage (cloud deployment)
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    async def write_file(self, path: str, content: bytes) -> bool:
        """Write file to storage."""
        pass

    @abstractmethod
    async def read_file(self, path: str) -> Optional[bytes]:
        """Read file from storage."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def list_files(self, prefix: str) -> list[str]:
        """List files with prefix."""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete file."""
        pass


class LocalFilesystemBackend(StorageBackend):
    """
    Local filesystem storage (Docker with volumes).

    Use for:
    - Docker Compose deployments
    - Single-node deployments
    - Development
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return self.base_dir / path

    async def write_file(self, path: str, content: bytes) -> bool:
        try:
            full_path = self._get_full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)
            logger.debug("File written to local filesystem", path=path)
            return True
        except Exception as e:
            logger.error("Failed to write file", path=path, error=str(e))
            return False

    async def read_file(self, path: str) -> Optional[bytes]:
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            return full_path.read_bytes()
        except Exception as e:
            logger.error("Failed to read file", path=path, error=str(e))
            return None

    async def exists(self, path: str) -> bool:
        return self._get_full_path(path).exists()

    async def list_files(self, prefix: str) -> list[str]:
        try:
            full_path = self._get_full_path(prefix)
            if not full_path.exists():
                return []

            files = []
            for item in full_path.rglob("*"):
                if item.is_file():
                    # Return relative path from base_dir
                    rel_path = item.relative_to(self.base_dir)
                    files.append(str(rel_path))
            return files
        except Exception as e:
            logger.error("Failed to list files", prefix=prefix, error=str(e))
            return []

    async def delete_file(self, path: str) -> bool:
        try:
            full_path = self._get_full_path(path)
            if full_path.exists():
                full_path.unlink()
                logger.debug("File deleted from local filesystem", path=path)
                return True
            return False
        except Exception as e:
            logger.error("Failed to delete file", path=path, error=str(e))
            return False


class S3Backend(StorageBackend):
    """
    S3-compatible object storage (cloud deployment).

    Use for:
    - AWS S3, MinIO, DigitalOcean Spaces, etc.
    - Multi-node cloud deployments
    - Production environments

    Requires:
    - boto3 library
    - S3_BUCKET environment variable
    - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    """

    def __init__(self, bucket: str, prefix: str = ""):
        try:
            import boto3
            self.s3 = boto3.client('s3')
            self.bucket = bucket
            self.prefix = prefix
            logger.info("S3 backend initialized", bucket=bucket, prefix=prefix)
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")

    def _get_s3_key(self, path: str) -> str:
        """Get S3 object key."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path

    async def write_file(self, path: str, content: bytes) -> bool:
        try:
            key = self._get_s3_key(path)
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=content)
            logger.debug("File written to S3", bucket=self.bucket, key=key)
            return True
        except Exception as e:
            logger.error("Failed to write to S3", path=path, error=str(e))
            return False

    async def read_file(self, path: str) -> Optional[bytes]:
        try:
            key = self._get_s3_key(path)
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error("Failed to read from S3", path=path, error=str(e))
            return None

    async def exists(self, path: str) -> bool:
        try:
            key = self._get_s3_key(path)
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False

    async def list_files(self, prefix: str) -> list[str]:
        try:
            key_prefix = self._get_s3_key(prefix)
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=key_prefix
            )

            files = []
            for obj in response.get('Contents', []):
                # Remove prefix to get relative path
                key = obj['Key']
                if self.prefix:
                    key = key.replace(f"{self.prefix}/", "")
                files.append(key)
            return files
        except Exception as e:
            logger.error("Failed to list S3 objects", prefix=prefix, error=str(e))
            return []

    async def delete_file(self, path: str) -> bool:
        try:
            key = self._get_s3_key(path)
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            logger.debug("File deleted from S3", bucket=self.bucket, key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete from S3", path=path, error=str(e))
            return False


class PostgreSQLBlobBackend(StorageBackend):
    """
    PostgreSQL BLOB storage (cloud deployment).

    Use for:
    - Small files (< 1GB)
    - Transactional file operations
    - When S3 is not available

    Schema:
        CREATE TABLE file_storage (
            path TEXT PRIMARY KEY,
            content BYTEA NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """

    def __init__(self, database_url: str):
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            self.engine = create_async_engine(database_url)
            logger.info("PostgreSQL blob backend initialized")
        except ImportError:
            raise RuntimeError("asyncpg not installed. Run: pip install asyncpg")

    async def write_file(self, path: str, content: bytes) -> bool:
        try:
            async with self.engine.begin() as conn:
                await conn.execute(
                    """
                    INSERT INTO file_storage (path, content, updated_at)
                    VALUES (:path, :content, NOW())
                    ON CONFLICT (path) DO UPDATE
                    SET content = EXCLUDED.content, updated_at = NOW()
                    """,
                    {"path": path, "content": content}
                )
            logger.debug("File written to PostgreSQL", path=path)
            return True
        except Exception as e:
            logger.error("Failed to write to PostgreSQL", path=path, error=str(e))
            return False

    async def read_file(self, path: str) -> Optional[bytes]:
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    "SELECT content FROM file_storage WHERE path = :path",
                    {"path": path}
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error("Failed to read from PostgreSQL", path=path, error=str(e))
            return None

    async def exists(self, path: str) -> bool:
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    "SELECT 1 FROM file_storage WHERE path = :path",
                    {"path": path}
                )
                return result.fetchone() is not None
        except:
            return False

    async def list_files(self, prefix: str) -> list[str]:
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    "SELECT path FROM file_storage WHERE path LIKE :prefix",
                    {"prefix": f"{prefix}%"}
                )
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error("Failed to list PostgreSQL files", prefix=prefix, error=str(e))
            return []

    async def delete_file(self, path: str) -> bool:
        try:
            async with self.engine.begin() as conn:
                await conn.execute(
                    "DELETE FROM file_storage WHERE path = :path",
                    {"path": path}
                )
            logger.debug("File deleted from PostgreSQL", path=path)
            return True
        except Exception as e:
            logger.error("Failed to delete from PostgreSQL", path=path, error=str(e))
            return False


# Factory function
def create_storage_backend() -> StorageBackend:
    """
    Create storage backend based on environment configuration.

    Environment Variables:
    - STORAGE_BACKEND: "local", "s3", or "postgresql" (default: "local")
    - S3_BUCKET: S3 bucket name (required for S3 backend)
    - S3_PREFIX: S3 key prefix (optional)
    - DATABASE_URL: PostgreSQL connection string (required for PostgreSQL backend)
    - DATA_DIR: Local filesystem base directory (default: /data)
    """
    backend_type = os.getenv("STORAGE_BACKEND", "local").lower()

    if backend_type == "s3":
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise ValueError("S3_BUCKET environment variable required for S3 backend")
        prefix = os.getenv("S3_PREFIX", "claude-agent")
        return S3Backend(bucket=bucket, prefix=prefix)

    elif backend_type == "postgresql":
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable required for PostgreSQL backend")
        return PostgreSQLBlobBackend(database_url=db_url)

    else:  # "local" or default
        data_dir = Path(os.getenv("DATA_DIR", "/data"))
        return LocalFilesystemBackend(base_dir=data_dir)


# Singleton instance
_storage_backend: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Get singleton storage backend instance."""
    global _storage_backend
    if _storage_backend is None:
        _storage_backend = create_storage_backend()
        logger.info("Storage backend created", type=type(_storage_backend).__name__)
    return _storage_backend
