from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "movie-api"
    database_url: str = ""  # bắt buộc từ env (Vault → cinehome-app-secrets)


    minio_endpoint: str = "minio.minio.svc.cluster.local:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""

    minio_secure: bool = False
    minio_bucket_movies: str = "movies"
    minio_bucket_posters: str = "posters"
    minio_bucket_raw: str = "raw"
    # Public base URL for browser (Route/Ingress tới MinIO API)
    minio_public_url: str = "https://minio-api-minio.apps.ocp01.npd.co"
    # Presign TTL seconds
    stream_url_ttl: int = 3600
    upload_url_ttl: int = 7200

    redis_url: str = ""
    # Bitnami Redis Sentinel — master name mặc định mymaster (tránh ReadOnlyError trên replica)
    redis_sentinel_master: str = "mymaster"
    redis_sentinel_port: int = 26379

    media_queue: str = "cinehome:media:jobs"

    cors_origins: str = "*"
    seed_demo_data: bool = True


settings = Settings()
