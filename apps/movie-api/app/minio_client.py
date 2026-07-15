from datetime import timedelta
from urllib.parse import urlparse

from minio import Minio

from app.config import settings


def get_minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def get_minio_public() -> Minio:
    """Client ký URL theo host công khai (Route) — chữ ký khớp browser PUT/GET."""
    public = urlparse(settings.minio_public_url)
    if not public.netloc:
        return get_minio()
    return Minio(
        public.netloc,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=(public.scheme or "https") == "https",
    )


def ensure_buckets(client: Minio | None = None) -> None:
    client = client or get_minio()
    for bucket in (
        settings.minio_bucket_movies,
        settings.minio_bucket_posters,
        settings.minio_bucket_raw,
    ):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def put_fileobj(
    bucket: str,
    key: str,
    fileobj,
    *,
    length: int | None = None,
    content_type: str = "application/octet-stream",
) -> None:
    client = get_minio()
    size = -1 if length is None or length < 0 else length
    kwargs: dict = {"content_type": content_type}
    if size < 0:
        kwargs["part_size"] = 16 * 1024 * 1024
    client.put_object(bucket, key, fileobj, size, **kwargs)


def public_object_url(bucket: str, key: str) -> str:
    if not key:
        return ""
    base = settings.minio_public_url.rstrip("/")
    return f"{base}/{bucket}/{key.lstrip('/')}"


def presigned_get_url(bucket: str, key: str, ttl: int | None = None) -> str:
    if not key:
        return ""
    client = get_minio_public()
    return client.presigned_get_object(
        bucket,
        key,
        expires=timedelta(seconds=ttl or settings.stream_url_ttl),
    )


def presigned_put_url(bucket: str, key: str, ttl: int | None = None) -> str:
    client = get_minio_public()
    return client.presigned_put_object(
        bucket,
        key,
        expires=timedelta(seconds=ttl or settings.upload_url_ttl),
    )
