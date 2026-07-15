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


def ensure_buckets(client: Minio | None = None) -> None:
    client = client or get_minio()
    for bucket in (settings.minio_bucket_movies, settings.minio_bucket_posters):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def public_object_url(bucket: str, key: str) -> str:
    if not key:
        return ""
    base = settings.minio_public_url.rstrip("/")
    return f"{base}/{bucket}/{key.lstrip('/')}"


def presigned_get_url(bucket: str, key: str, ttl: int | None = None) -> str:
    if not key:
        return ""
    client = get_minio()
    # Internal presign host may differ from public Route — rewrite host for browser.
    url = client.presigned_get_object(
        bucket,
        key,
        expires=ttl or settings.stream_url_ttl,
    )
    public = urlparse(settings.minio_public_url)
    parsed = urlparse(url)
    # Keep path + query from MinIO, swap scheme/netloc to public Route
    return parsed._replace(scheme=public.scheme, netloc=public.netloc).geturl()
