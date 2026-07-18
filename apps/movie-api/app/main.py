from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import Episode, Movie, Season, Series, get_db, init_db
from app.minio_client import ensure_buckets, presigned_put_url, public_object_url, put_fileobj
from app.queue import enqueue_media_job
from app.seed import artwork_for_slug, seed_movies, seed_series, sync_series_artwork

app = FastAPI(title=settings.app_name, version="1.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def media_url(key: str, bucket: str | None = None) -> str:
    if not key:
        return ""
    if key.startswith("http://") or key.startswith("https://") or key.startswith("/"):
        return key
    return public_object_url(bucket or settings.minio_bucket_posters, key)


# —— Movies (legacy) ——

class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str
    year: int
    genre: str
    duration_minutes: int
    poster_url: str = ""
    hls_key: str = ""


class StreamOut(BaseModel):
    hls_url: str
    expires_in: int
    episode_id: int | None = None
    movie_id: int | None = None
    subtitle_url: str = ""


def subtitle_key_from_hls(hls_key: str) -> str:
    """movies/.../master.m3u8 → same folder subs.vi.vtt"""
    if "/" not in hls_key:
        return "subs.vi.vtt"
    return hls_key.rsplit("/", 1)[0] + "/subs.vi.vtt"


class MovieCreate(BaseModel):
    slug: str
    title: str
    description: str = ""
    year: int = 0
    genre: str = ""
    duration_minutes: int = 0
    poster_key: str = ""
    hls_key: str = ""


def to_movie_out(m: Movie) -> MovieOut:
    return MovieOut(
        id=m.id,
        slug=m.slug,
        title=m.title,
        description=m.description,
        year=m.year,
        genre=m.genre,
        duration_minutes=m.duration_minutes,
        poster_url=media_url(m.poster_key),
        hls_key=m.hls_key,
    )


# —— Series ——

class EpisodeOut(BaseModel):
    id: int
    number: int
    title: str
    description: str
    duration_minutes: int
    hls_key: str
    poster_url: str = ""
    status: str = "PENDING"
    season_number: int = 0
    series_slug: str = ""
    series_title: str = ""


class SeasonOut(BaseModel):
    id: int
    number: int
    title: str
    episodes: list[EpisodeOut] = Field(default_factory=list)


class SeriesOut(BaseModel):
    id: int
    slug: str
    title: str
    english_title: str
    description: str
    year_start: int
    franchise: str
    genre: str
    rating: str
    poster_url: str = ""
    backdrop_url: str = ""
    seasons: list[SeasonOut] = Field(default_factory=list)
    episode_count: int = 0


class SeriesCard(BaseModel):
    id: int
    slug: str
    title: str
    english_title: str
    description: str
    year_start: int
    franchise: str
    genre: str
    rating: str
    poster_url: str = ""
    backdrop_url: str = ""
    episode_count: int = 0


class HomeOut(BaseModel):
    featured: SeriesOut | None = None
    rows: list[dict]


def episode_count(series: Series) -> int:
    return sum(len(s.episodes) for s in series.seasons)


def to_episode_out(ep: Episode, season: Season | None = None, series: Series | None = None) -> EpisodeOut:
    season = season or ep.season
    series = series or (season.series if season else None)
    return EpisodeOut(
        id=ep.id,
        number=ep.number,
        title=ep.title,
        description=ep.description,
        duration_minutes=ep.duration_minutes,
        hls_key=ep.hls_key,
        poster_url=media_url(ep.poster_key or (series.poster_key if series else "")),
        status=getattr(ep, "status", None) or "PENDING",
        season_number=season.number if season else 0,
        series_slug=series.slug if series else "",
        series_title=series.title if series else "",
    )


def to_series_out(series: Series, include_seasons: bool = True) -> SeriesOut:
    seasons_out: list[SeasonOut] = []
    if include_seasons:
        for season in series.seasons:
            seasons_out.append(
                SeasonOut(
                    id=season.id,
                    number=season.number,
                    title=season.title,
                    episodes=[to_episode_out(ep, season, series) for ep in season.episodes],
                )
            )
    return SeriesOut(
        id=series.id,
        slug=series.slug,
        title=series.title,
        english_title=series.english_title,
        description=series.description,
        year_start=series.year_start,
        franchise=series.franchise,
        genre=series.genre,
        rating=series.rating,
        poster_url=media_url(series.poster_key),
        backdrop_url=media_url(series.backdrop_key),
        seasons=seasons_out,
        episode_count=episode_count(series),
    )


def to_series_card(series: Series) -> SeriesCard:
    return SeriesCard(
        id=series.id,
        slug=series.slug,
        title=series.title,
        english_title=series.english_title,
        description=series.description,
        year_start=series.year_start,
        franchise=series.franchise,
        genre=series.genre,
        rating=series.rating,
        poster_url=media_url(series.poster_key),
        backdrop_url=media_url(series.backdrop_key),
        episode_count=episode_count(series),
    )


def load_series_query(db: Session):
    return (
        db.query(Series)
        .options(joinedload(Series.seasons).joinedload(Season.episodes))
        .order_by(Series.year_start.asc(), Series.title.asc())
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    try:
        ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] minio buckets: {exc}")
    if settings.seed_demo_data:
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            nm = seed_movies(db)
            ns = seed_series(db)
            na = sync_series_artwork(db)
            if nm or ns or na:
                print(f"[seed] movies={nm} series={ns} artwork={na}")
        finally:
            db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/home", response_model=HomeOut)
def home(db: Session = Depends(get_db)):
    rows_series = load_series_query(db).all()
    featured = to_series_out(rows_series[0], include_seasons=False) if rows_series else None
    # Prefer BTAS as hero when present
    for s in rows_series:
        if s.slug == "batman-animated":
            featured = to_series_out(s, include_seasons=False)
            break
    else:
        for s in rows_series:
            if s.franchise == "batman":
                featured = to_series_out(s, include_seasons=False)
                break
    return HomeOut(
        featured=featured,
        rows=[
            {
                "title": "Animation series",
                "items": [to_series_card(s).model_dump() for s in rows_series],
            },
            {
                "title": "X-Men",
                "items": [to_series_card(s).model_dump() for s in rows_series if s.franchise == "x-men"],
            },
            {
                "title": "Spider-Man",
                "items": [to_series_card(s).model_dump() for s in rows_series if s.franchise == "spiderman"],
            },
            {
                "title": "Batman",
                "items": [to_series_card(s).model_dump() for s in rows_series if s.franchise == "batman"],
            },
        ],
    )


@app.get("/api/series", response_model=list[SeriesCard])
def list_series(
    q: str | None = Query(None),
    franchise: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = load_series_query(db)
    items = query.all()
    if franchise:
        items = [s for s in items if s.franchise == franchise]
    if q:
        like = q.lower()
        items = [
            s
            for s in items
            if like in s.title.lower()
            or like in s.english_title.lower()
            or like in s.description.lower()
        ]
    return [to_series_card(s) for s in items]


@app.get("/api/series/{slug}", response_model=SeriesOut)
def get_series(slug: str, db: Session = Depends(get_db)):
    series = load_series_query(db).filter(Series.slug == slug).first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return to_series_out(series)


@app.get("/api/episodes/{episode_id}", response_model=EpisodeOut)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    ep = (
        db.query(Episode)
        .options(joinedload(Episode.season).joinedload(Season.series))
        .filter(Episode.id == episode_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return to_episode_out(ep)


@app.get("/api/episodes/{episode_id}/stream", response_model=StreamOut)
def stream_episode(episode_id: int, db: Session = Depends(get_db)):
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if getattr(ep, "status", None) == "PROCESSING":
        raise HTTPException(status_code=409, detail="Đang convert HLS, thử lại sau")
    if getattr(ep, "status", None) == "FAILED":
        raise HTTPException(status_code=409, detail=ep.error_message or "Convert failed")
    if not ep.hls_key:
        raise HTTPException(status_code=404, detail="HLS not ready — upload/convert trước")
    url = public_object_url(settings.minio_bucket_movies, ep.hls_key)
    sub_url = public_object_url(settings.minio_bucket_movies, subtitle_key_from_hls(ep.hls_key))
    return StreamOut(
        episode_id=ep.id,
        hls_url=url,
        subtitle_url=sub_url,
        expires_in=settings.stream_url_ttl,
    )


class EpisodeCreate(BaseModel):
    title: str
    number: int
    description: str = ""
    duration_minutes: int = 22


class SeriesCreate(BaseModel):
    slug: str
    title: str
    english_title: str = ""
    description: str = ""
    year_start: int = 0
    franchise: str = "x-men"
    genre: str = "Hoạt hình"
    poster_key: str = "/movies/poster-1.png"
    backdrop_key: str = "/movies/hero-backdrop.png"
    rating: str = "8.5"


def _guess_franchise(slug: str) -> str:
    s = slug.lower()
    if s.startswith("x-men") or s.startswith("xmen"):
        return "x-men"
    if "spider" in s:
        return "spiderman"
    if "batman" in s:
        return "batman"
    return "other"


@app.post("/api/series", response_model=SeriesOut, status_code=201)
def create_series(body: SeriesCreate, db: Session = Depends(get_db)):
    exists = db.query(Series).filter(Series.slug == body.slug).first()
    if exists:
        raise HTTPException(status_code=409, detail="Series already exists")
    series = Series(
        slug=body.slug,
        title=body.title,
        english_title=body.english_title or body.title,
        description=body.description,
        year_start=body.year_start,
        franchise=body.franchise or _guess_franchise(body.slug),
        genre=body.genre,
        poster_key=body.poster_key,
        backdrop_key=body.backdrop_key,
        rating=body.rating,
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    return to_series_out(series, include_seasons=True)


class UploadInitOut(BaseModel):
    episode_id: int
    raw_key: str
    upload_url: str
    subtitle_raw_key: str = ""
    subtitle_upload_url: str = ""
    expires_in: int


@app.post("/api/series/{slug}/seasons/{season_number}/episodes", response_model=EpisodeOut, status_code=201)
def create_episode(slug: str, season_number: int, body: EpisodeCreate, db: Session = Depends(get_db)):
    series = load_series_query(db).filter(Series.slug == slug).first()
    if not series:
        # Auto-create series so Windows batch SyncCatalog works without seed deploy
        pretty_titles = {
            "x-men-97": "X-Men '97",
            "batman-animated": "Batman: The Animated Series",
            "batman-new-adventures": "The New Batman Adventures",
            "the-batman-2004": "The Batman (2004)",
            "batman-phantasm": "Batman: Mask of the Phantasm",
            "batman-subzero": "Batman & Mr. Freeze: SubZero",
            "batman-return-of-the-joker": "Batman Beyond: Return of the Joker",
            "spiderman-animated": "Spider-Man: The Animated Series",
        }
        pretty = pretty_titles.get(slug, slug.replace("-", " ").title())
        poster_key, backdrop_key = artwork_for_slug(slug)
        series = Series(
            slug=slug,
            title=pretty,
            english_title=pretty,
            description="",
            year_start=0,
            franchise=_guess_franchise(slug),
            genre="Hoạt hình",
            poster_key=poster_key,
            backdrop_key=backdrop_key,
            rating="8.5",
        )
        db.add(series)
        db.flush()
    season = next((s for s in series.seasons if s.number == season_number), None)
    if not season:
        season = Season(series_id=series.id, number=season_number, title=f"Season {season_number}")
        db.add(season)
        db.flush()
    exists = next((e for e in season.episodes if e.number == body.number), None)
    if exists:
        raise HTTPException(status_code=409, detail="Episode number already exists")
    ep_code = f"s{season_number:02d}e{body.number:02d}"
    ep = Episode(
        season_id=season.id,
        number=body.number,
        title=body.title,
        description=body.description,
        duration_minutes=body.duration_minutes,
        hls_key=f"{series.slug}/{ep_code}/master.m3u8",
        poster_key=series.poster_key,
        status="READY",
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return to_episode_out(ep, season, series)


@app.post("/api/episodes/{episode_id}/upload-init", response_model=UploadInitOut)
def upload_init(
    episode_id: int,
    filename: str = Query("video.mp4"),
    with_subtitle: bool = Query(False),
    db: Session = Depends(get_db),
):
    ep = (
        db.query(Episode)
        .options(joinedload(Episode.season).joinedload(Season.series))
        .filter(Episode.id == episode_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    series = ep.season.series
    ep_code = f"s{ep.season.number:02d}e{ep.number:02d}"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp4"
    if ext not in ("mp4", "mkv", "avi", "mov", "webm"):
        ext = "mp4"
    raw_key = f"{series.slug}/{ep_code}/source.{ext}"
    ep.raw_key = raw_key
    ep.status = "UPLOADING"
    ep.error_message = ""
    if not ep.hls_key:
        ep.hls_key = f"{series.slug}/{ep_code}/master.m3u8"

    sub_key = ""
    sub_url = ""
    if with_subtitle:
        sub_key = f"{series.slug}/{ep_code}/source.srt"
        ep.subtitle_raw_key = sub_key
        sub_url = presigned_put_url(settings.minio_bucket_raw, sub_key)

    db.commit()
    upload_url = presigned_put_url(settings.minio_bucket_raw, raw_key)
    return UploadInitOut(
        episode_id=ep.id,
        raw_key=raw_key,
        upload_url=upload_url,
        subtitle_raw_key=sub_key,
        subtitle_upload_url=sub_url,
        expires_in=settings.upload_url_ttl,
    )


@app.post("/api/episodes/{episode_id}/upload-complete", response_model=EpisodeOut)
def upload_complete(episode_id: int, db: Session = Depends(get_db)):
    ep = (
        db.query(Episode)
        .options(joinedload(Episode.season).joinedload(Season.series))
        .filter(Episode.id == episode_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not ep.raw_key:
        raise HTTPException(status_code=400, detail="Chưa upload-init / thiếu raw_key")
    ep.status = "PROCESSING"
    ep.error_message = ""
    db.commit()

    series = ep.season.series
    try:
        enqueue_media_job(
            {
                "episode_id": ep.id,
                "series_slug": series.slug,
                "season_number": ep.season.number,
                "episode_number": ep.number,
                "raw_key": ep.raw_key,
                "subtitle_raw_key": ep.subtitle_raw_key or "",
                "hls_key": ep.hls_key,
            }
        )
    except Exception as exc:  # noqa: BLE001
        ep.status = "FAILED"
        ep.error_message = f"enqueue failed: {exc}"
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.refresh(ep)
    return to_episode_out(ep)


@app.post("/api/episodes/{episode_id}/upload", response_model=EpisodeOut)
def upload_episode_files(
    episode_id: int,
    video: UploadFile = File(...),
    subtitle: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """Upload qua API (cùng origin / Next rewrite) — tránh CORS browser→MinIO."""
    ep = (
        db.query(Episode)
        .options(joinedload(Episode.season).joinedload(Season.series))
        .filter(Episode.id == episode_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    series = ep.season.series
    ep_code = f"s{ep.season.number:02d}e{ep.number:02d}"
    filename = video.filename or "video.mp4"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp4"
    if ext not in ("mp4", "mkv", "avi", "mov", "webm"):
        ext = "mp4"
    raw_key = f"{series.slug}/{ep_code}/source.{ext}"
    ep.raw_key = raw_key
    ep.status = "UPLOADING"
    ep.error_message = ""
    if not ep.hls_key:
        ep.hls_key = f"{series.slug}/{ep_code}/master.m3u8"

    sub_key = ""
    if subtitle is not None and subtitle.filename:
        sub_key = f"{series.slug}/{ep_code}/source.srt"
        ep.subtitle_raw_key = sub_key
    db.commit()

    try:
        put_fileobj(
            settings.minio_bucket_raw,
            raw_key,
            video.file,
            length=getattr(video, "size", None),
            content_type=video.content_type or "video/mp4",
        )
        if sub_key and subtitle is not None:
            put_fileobj(
                settings.minio_bucket_raw,
                sub_key,
                subtitle.file,
                length=getattr(subtitle, "size", None),
                content_type="application/x-subrip",
            )
    except Exception as exc:  # noqa: BLE001
        ep.status = "FAILED"
        ep.error_message = f"upload failed: {exc}"
        db.commit()
        print(f"[upload] ep={episode_id} FAILED: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        return upload_complete(episode_id, db)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"[upload] ep={episode_id} complete FAILED: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/movies", response_model=list[MovieOut])
def list_movies(
    q: str | None = Query(None),
    genre: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Movie).order_by(Movie.year.desc(), Movie.title.asc())
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Movie.title.ilike(like), Movie.description.ilike(like)))
    if genre:
        query = query.filter(Movie.genre.ilike(genre))
    return [to_movie_out(m) for m in query.all()]


@app.get("/api/movies/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return to_movie_out(movie)


@app.get("/api/movies/{movie_id}/stream", response_model=StreamOut)
def stream_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    if not movie.hls_key:
        raise HTTPException(status_code=404, detail="HLS not configured")
    url = public_object_url(settings.minio_bucket_movies, movie.hls_key)
    sub_url = public_object_url(settings.minio_bucket_movies, subtitle_key_from_hls(movie.hls_key))
    return StreamOut(
        movie_id=movie.id,
        hls_url=url,
        subtitle_url=sub_url,
        expires_in=settings.stream_url_ttl,
    )


@app.post("/api/movies", response_model=MovieOut, status_code=201)
def create_movie(body: MovieCreate, db: Session = Depends(get_db)):
    if db.query(Movie).filter(Movie.slug == body.slug).first():
        raise HTTPException(status_code=409, detail="slug already exists")
    movie = Movie(**body.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return to_movie_out(movie)


@app.get("/api/genres")
def list_genres(db: Session = Depends(get_db)):
    movie_genres = [r[0] for r in db.query(Movie.genre).distinct().all() if r[0]]
    series_genres = [r[0] for r in db.query(Series.genre).distinct().all() if r[0]]
    return {"genres": sorted(set(movie_genres + series_genres))}
