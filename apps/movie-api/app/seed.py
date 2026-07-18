from sqlalchemy.orm import Session

from app.db import Episode, Movie, Season, Series

DEMO_MOVIES = [
    {
        "slug": "demo-night-drive",
        "title": "Night Drive",
        "description": "Phim demo — thay hls_key bằng path HLS thật trên MinIO.",
        "year": 2024,
        "genre": "Action",
        "duration_minutes": 112,
        "poster_key": "night-drive.jpg",
        "hls_key": "night-drive/master.m3u8",
    },
]

# Scaffold 3 animation franchises — upload HLS theo hls_key khi có file thật
ANIMATION_SERIES = [
    {
        "slug": "x-men-animated",
        "title": "X-Men Animations",
        "english_title": "X-Men: The Animated Series",
        "description": (
            "Đội X-Men đối đầu nguy hiểm đột biến và thế lực thù địch. "
            "Series hoạt hình kinh điển — scaffold để đổ HLS từng tập lên MinIO."
        ),
        "year_start": 1992,
        "franchise": "x-men",
        "genre": "Hoạt hình",
        "poster_key": "/movies/x-men-tas-poster.jpg",
        "backdrop_key": "/movies/x-men-tas-backdrop.jpg",
        "rating": "8.8",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("Night of the Sentinels (1)", "Mutant Registration và cuộc tấn đầu tiên với Sentinels."),
                    ("Night of the Sentinels (2)", "X-Men giải cứu các đột biến bị giam giữ."),
                    ("Enter Magneto", "Magneto xuất hiện — xung đột triết lý với Xavier."),
                    ("Deadly Reunions", "Wolverine đối mặt quá khứ."),
                ],
            },
            {
                "number": 2,
                "title": "Season 2",
                "episodes": [
                    ("Till Death Do Us Part (1)", "Morph trở lại gây chia rẽ."),
                    ("Till Death Do Us Part (2)", "Bí mật Morph và Mister Sinister."),
                    ("Whatever It Takes", "Storm mất sức mạnh trong trận chiến."),
                ],
            },
        ],
    },
    {
        "slug": "x-men-97",
        "title": "X-Men '97",
        "english_title": "X-Men '97",
        "description": (
            "Tái sinh X-Men The Animated Series — upload HLS qua script Windows "
            "hoặc /admin. Folder nguồn: X97."
        ),
        "year_start": 2024,
        "franchise": "x-men",
        "genre": "Hoạt hình",
        "poster_key": "/movies/x-men-97-poster.webp",
        "backdrop_key": "/movies/x-men-97-backdrop.webp",
        "rating": "9.0",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("Episode 1", "Tập 1 — thay bằng upload thật."),
                ],
            },
        ],
    },
    {
        "slug": "spiderman-animated",
        "title": "Spider-Man Animations",
        "english_title": "Spider-Man: The Animated Series",
        "description": (
            "Peter Parker cân bằng đời sống sinh viên và nhiệm vụ Người Nhện. "
            "Series hoạt hình 90s — sẵn sàng gắn HLS theo từng tập."
        ),
        "year_start": 1994,
        "franchise": "spiderman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/spiderman-tas-poster.jpg",
        "backdrop_key": "/movies/spiderman-tas-backdrop.jpg",
        "rating": "8.5",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("Night of the Lizard", "Dr. Connors biến thành Lizard."),
                    ("The Spider Slayer", "Kingpin thuê Alistair Smythe."),
                    ("Return of the Spider Slayers", "Cuộc chiến với các robot săn nhện."),
                    ("Doctor Octopus: Armed and Dangerous", "Doc Ock xuất hiện."),
                ],
            },
            {
                "number": 2,
                "title": "Season 2",
                "episodes": [
                    ("The Insidious Six", "Liên minh phản diện chống Spider-Man."),
                    ("Battle of the Insidious Six", "Peter bị lộ danh tính?"),
                    ("Hydro-Man", "Mary Jane và thảm họa nước."),
                ],
            },
        ],
    },
    {
        "slug": "batman-animated",
        "title": "Batman: The Animated Series",
        "english_title": "Batman: The Animated Series",
        "description": (
            "Hiệp sĩ bóng đêm bảo vệ Gotham trong phong cách noir hoạt hình. "
            "Series kinh điển 1992–95 — upload HLS từng tập lên MinIO."
        ),
        "year_start": 1992,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/batman-tas-poster.jpg",
        "backdrop_key": "/movies/batman-tas-backdrop.jpg",
        "rating": "9.0",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("On Leather Wings", "Man-Bat và khoa học điên loạn."),
                    ("Christmas with the Joker", "Joker phá đám Noel Gotham."),
                    ("Nothing to Fear", "Scarecrow tận dụng nỗi sợ."),
                    ("The Last Laugh", "Joker và khí cười gây hỗn loạn."),
                ],
            },
            {
                "number": 2,
                "title": "Season 2",
                "episodes": [
                    ("Eternal Youth", "Ra's al Ghul và elixir trẻ hóa."),
                    ("Perchance to Dream", "Bruce Wayne trong thế giới không có Batman."),
                    ("Robin's Reckoning (1)", "Quá khứ của Dick Grayson."),
                ],
            },
            {
                "number": 3,
                "title": "Season 3",
                "episodes": [
                    ("Shadow of the Bat (1)", "Batman bị buộc tội — Batgirl xuất hiện."),
                    ("The Demon's Quest (1)", "Ra's al Ghul trở lại."),
                    ("Harlequinade", "Harley Quinn và Joker."),
                ],
            },
        ],
    },
    {
        "slug": "batman-new-adventures",
        "title": "The New Batman Adventures",
        "english_title": "The New Batman Adventures",
        "description": (
            "Tiếp nối BTAS với thiết kế mới — Batgirl, Nightwing và thế hệ phản diện "
            "Gotham thập niên 90 muộn."
        ),
        "year_start": 1997,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/batman-tnba-poster.jpg",
        "backdrop_key": "/movies/batman-tnba-backdrop.jpg",
        "rating": "8.7",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("Holiday Knights", "Ba câu chuyện đêm giao thừa Gotham."),
                    ("Sins of the Father", "Tim Drake trở thành Robin mới."),
                    ("Mad Love", "Nguồn gốc Harley Quinn."),
                ],
            },
        ],
    },
    {
        "slug": "the-batman-2004",
        "title": "The Batman (2004)",
        "english_title": "The Batman",
        "description": (
            "Bruce Wayne những năm đầu làm Batman — phong cách góc cạnh, "
            "đối đầu Joker, Penguin và liên minh phản diện mới."
        ),
        "year_start": 2004,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/the-batman-2004-poster.jpg",
        "backdrop_key": "/movies/the-batman-2004-backdrop.jpg",
        "rating": "7.5",
        "seasons": [
            {
                "number": 1,
                "title": "Season 1",
                "episodes": [
                    ("The Bat in the Belfry", "Batman đối đầu Joker lần đầu trong series."),
                    ("Traction", "Bane xuất hiện."),
                    ("Call of the Cobblepot", "Penguin trở lại Gotham."),
                ],
            },
        ],
    },
    {
        "slug": "batman-phantasm",
        "title": "Batman: Mask of the Phantasm",
        "english_title": "Batman: Mask of the Phantasm",
        "description": (
            "Phim điện ảnh BTAS — Batman bị truy nã khi Phantasm săn tội phạm Gotham; "
            "quá khứ với Andrea Beaumont trở lại."
        ),
        "year_start": 1993,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/batman-phantasm-poster.jpg",
        "backdrop_key": "/movies/batman-phantasm-backdrop.jpg",
        "rating": "8.5",
        "seasons": [
            {
                "number": 1,
                "title": "Film",
                "episodes": [
                    ("Mask of the Phantasm", "Batman, Joker và bí ẩn Phantasm."),
                ],
            },
        ],
    },
    {
        "slug": "batman-subzero",
        "title": "Batman & Mr. Freeze: SubZero",
        "english_title": "Batman & Mr. Freeze: SubZero",
        "description": (
            "Mr. Freeze bắt cóc Barbara Gordon để cứu vợ — Batman và Robin "
            "đua với thời gian trong phim direct-to-video BTAS."
        ),
        "year_start": 1998,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/batman-subzero-poster.jpg",
        "backdrop_key": "/movies/batman-subzero-backdrop.jpg",
        "rating": "7.2",
        "seasons": [
            {
                "number": 1,
                "title": "Film",
                "episodes": [
                    ("SubZero", "Mr. Freeze và kế hoạch cứu Nora."),
                ],
            },
        ],
    },
    {
        "slug": "batman-return-of-the-joker",
        "title": "Batman Beyond: Return of the Joker",
        "english_title": "Batman Beyond: Return of the Joker",
        "description": (
            "Joker trở lại Neo-Gotham — Terry McGinnis và Bruce Wayne "
            "đối mặt bí mật đen tối nhất của Batman Beyond."
        ),
        "year_start": 2000,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/batman-rotoj-poster.jpg",
        "backdrop_key": "/movies/batman-rotoj-backdrop.jpg",
        "rating": "8.0",
        "seasons": [
            {
                "number": 1,
                "title": "Film",
                "episodes": [
                    ("Return of the Joker", "Joker, Terry, và quá khứ của Tim Drake."),
                ],
            },
        ],
    },
]

# poster/backdrop paths under Next.js public/ — used by seed + sync on API startup
SERIES_ARTWORK: dict[str, tuple[str, str]] = {
    "x-men-animated": ("/movies/x-men-tas-poster.jpg", "/movies/x-men-tas-backdrop.jpg"),
    "x-men-97": ("/movies/x-men-97-poster.webp", "/movies/x-men-97-backdrop.webp"),
    "spiderman-animated": ("/movies/spiderman-tas-poster.jpg", "/movies/spiderman-tas-backdrop.jpg"),
    "batman-animated": ("/movies/batman-tas-poster.jpg", "/movies/batman-tas-backdrop.jpg"),
    "batman-new-adventures": ("/movies/batman-tnba-poster.jpg", "/movies/batman-tnba-backdrop.jpg"),
    "the-batman-2004": ("/movies/the-batman-2004-poster.jpg", "/movies/the-batman-2004-backdrop.jpg"),
    "batman-phantasm": ("/movies/batman-phantasm-poster.jpg", "/movies/batman-phantasm-backdrop.jpg"),
    "batman-subzero": ("/movies/batman-subzero-poster.jpg", "/movies/batman-subzero-backdrop.jpg"),
    "batman-return-of-the-joker": ("/movies/batman-rotoj-poster.jpg", "/movies/batman-rotoj-backdrop.jpg"),
}


def artwork_for_slug(slug: str) -> tuple[str, str]:
    return SERIES_ARTWORK.get(
        slug,
        ("/movies/poster-1.png", "/movies/hero-backdrop.png"),
    )


def seed_movies(db: Session) -> int:
    created = 0
    for item in DEMO_MOVIES:
        if db.query(Movie).filter(Movie.slug == item["slug"]).first():
            continue
        db.add(Movie(**item))
        created += 1
    if created:
        db.commit()
    return created


def seed_series(db: Session) -> int:
    created_series = 0
    for raw in ANIMATION_SERIES:
        if db.query(Series).filter(Series.slug == raw["slug"]).first():
            continue
        seasons_data = raw["seasons"]
        series = Series(
            slug=raw["slug"],
            title=raw["title"],
            english_title=raw["english_title"],
            description=raw["description"],
            year_start=raw["year_start"],
            franchise=raw["franchise"],
            genre=raw["genre"],
            poster_key=raw["poster_key"],
            backdrop_key=raw["backdrop_key"],
            rating=raw["rating"],
        )
        db.add(series)
        db.flush()
        for s in seasons_data:
            season = Season(series_id=series.id, number=s["number"], title=s["title"])
            db.add(season)
            db.flush()
            for idx, (title, desc) in enumerate(s["episodes"], start=1):
                ep_code = f"s{s['number']:02d}e{idx:02d}"
                db.add(
                    Episode(
                        season_id=season.id,
                        number=idx,
                        title=title,
                        description=desc,
                        duration_minutes=22,
                        hls_key=f"{series.slug}/{ep_code}/master.m3u8",
                        poster_key=series.poster_key,
                    )
                )
        created_series += 1
    if created_series:
        db.commit()
    return created_series


def sync_series_artwork(db: Session) -> int:
    """Update artwork for existing rows; seed_series intentionally skips them."""
    updated = 0
    changed = False
    for slug, (poster_key, backdrop_key) in SERIES_ARTWORK.items():
        series = db.query(Series).filter(Series.slug == slug).first()
        if not series:
            continue
        if series.poster_key != poster_key or series.backdrop_key != backdrop_key:
            series.poster_key = poster_key
            series.backdrop_key = backdrop_key
            updated += 1
            changed = True
        for season in series.seasons:
            for episode in season.episodes:
                if episode.poster_key != poster_key:
                    episode.poster_key = poster_key
                    changed = True
    if changed:
        db.commit()
    return updated
