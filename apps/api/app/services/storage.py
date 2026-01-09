"""MinIO-backed storage helpers for uploads and exports."""

from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.settings import settings

_client: Minio | None = None


def get_client() -> Minio:
    """Get the MinIO client instance."""
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


async def init_storage() -> None:
    """Initialize storage bucket."""
    client = get_client()
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except S3Error as e:
        # Bucket might already exist
        if e.code != "BucketAlreadyOwnedByYou":
            raise


async def upload_file(
    object_key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload a file to storage."""
    client = get_client()
    client.put_object(
        settings.minio_bucket,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_key


async def download_file(object_key: str) -> bytes:
    """Download a file from storage."""
    client = get_client()
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def get_presigned_url(object_key: str, expires_hours: int = 1) -> str:
    """Get a presigned URL for downloading a file."""
    from datetime import timedelta

    client = get_client()
    return client.presigned_get_object(
        settings.minio_bucket,
        object_key,
        expires=timedelta(hours=expires_hours),
    )


async def delete_file(object_key: str) -> None:
    """Delete a file from storage."""
    client = get_client()
    client.remove_object(settings.minio_bucket, object_key)


async def object_exists(object_key: str) -> bool:
    """Check whether an object exists in storage."""
    client = get_client()
    try:
        client.stat_object(settings.minio_bucket, object_key)
        return True
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            return False
        raise
