from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""

    minio_endpoint: str = "minio.minio.svc.cluster.local:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_bucket_movies: str = "movies"
    minio_bucket_raw: str = "raw"

    redis_url: str = ""

    media_queue: str = "cinehome:media:jobs"

    work_dir: str = "/tmp/cinehome-work"
    ffmpeg_crf: int = 22
    hls_time: int = 6


settings = Settings()
