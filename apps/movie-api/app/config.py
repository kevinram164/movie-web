from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "movie-api"
    database_url: str = "postgresql+psycopg2://movie:movie@postgres-ha-postgresql.postgres.svc.cluster.local:5432/movie"

    minio_endpoint: str = "minio.minio.svc.cluster.local:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_movies: str = "movies"
    minio_bucket_posters: str = "posters"
    # Public base URL for browser (Route/Ingress tới MinIO API)
    minio_public_url: str = "https://minio-api-minio.apps.ocp01.npd.co"
    # Presign TTL seconds
    stream_url_ttl: int = 3600

    cors_origins: str = "*"
    seed_demo_data: bool = True


settings = Settings()
