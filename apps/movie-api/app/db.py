from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int] = mapped_column(Integer, default=0)
    genre: Mapped[str] = mapped_column(String(128), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    poster_key: Mapped[str] = mapped_column(String(512), default="")
    hls_key: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    english_title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    year_start: Mapped[int] = mapped_column(Integer, default=0)
    franchise: Mapped[str] = mapped_column(String(64), index=True)  # x-men | spiderman | batman
    genre: Mapped[str] = mapped_column(String(128), default="Hoạt hình")
    poster_key: Mapped[str] = mapped_column(String(512), default="")
    backdrop_key: Mapped[str] = mapped_column(String(512), default="")
    rating: Mapped[str] = mapped_column(String(16), default="8.5")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
        order_by="Season.number",
    )


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255), default="")

    series: Mapped["Series"] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="Episode.number",
    )


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=22)
    hls_key: Mapped[str] = mapped_column(String(512), default="")
    poster_key: Mapped[str] = mapped_column(String(512), default="")
    # PENDING | UPLOADING | PROCESSING | READY | FAILED
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    raw_key: Mapped[str] = mapped_column(String(512), default="")
    subtitle_raw_key: Mapped[str] = mapped_column(String(512), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")

    season: Mapped["Season"] = relationship(back_populates="episodes")


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_episode_columns()


def _migrate_episode_columns() -> None:
    """Thêm cột mới nếu DB đã tạo trước đó (Postgres)."""
    from sqlalchemy import text

    alters = [
        "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'PENDING'",
        "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS raw_key VARCHAR(512) DEFAULT ''",
        "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS subtitle_raw_key VARCHAR(512) DEFAULT ''",
        "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT ''",
    ]
    try:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] migrate episodes: {exc}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
