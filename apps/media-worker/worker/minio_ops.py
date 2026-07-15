from pathlib import Path

from minio import Minio

from worker.config import settings


def get_minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def download_object(bucket: str, key: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    get_minio().fget_object(bucket, key, str(dest))


def upload_dir(local_dir: Path, bucket: str, prefix: str) -> None:
    client = get_minio()
    prefix = prefix.rstrip("/")
    for path in local_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(local_dir).as_posix()
        object_name = f"{prefix}/{rel}"
        content_type = "application/octet-stream"
        if path.suffix == ".m3u8":
            content_type = "application/vnd.apple.mpegurl"
        elif path.suffix == ".ts":
            content_type = "video/mp2t"
        elif path.suffix == ".vtt":
            content_type = "text/vtt"
        client.fput_object(bucket, object_name, str(path), content_type=content_type)
