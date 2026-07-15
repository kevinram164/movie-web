from sqlalchemy import create_engine, text

from worker.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def set_episode_status(episode_id: int, status: str, error_message: str = "", hls_key: str | None = None) -> None:
    sets = ["status = :status", "error_message = :error"]
    params: dict = {"id": episode_id, "status": status, "error": error_message or ""}
    if hls_key is not None:
        sets.append("hls_key = :hls_key")
        params["hls_key"] = hls_key
    sql = text(f"UPDATE episodes SET {', '.join(sets)} WHERE id = :id")
    with engine.begin() as conn:
        conn.execute(sql, params)
