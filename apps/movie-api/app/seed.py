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
        "poster_key": "/movies/poster-1.png",
        "backdrop_key": "/movies/hero-backdrop.png",
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
        "poster_key": "/movies/poster-2.png",
        "backdrop_key": "/movies/hero-backdrop.png",
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
        "title": "Batman Animations",
        "english_title": "Batman: The Animated Series",
        "description": (
            "Hiệp sĩ bóng đêm bảo vệ Gotham trong phong cách noir hoạt hình. "
            "Scaffold seasons/episodes — upload HLS khi sẵn sàng."
        ),
        "year_start": 1992,
        "franchise": "batman",
        "genre": "Hoạt hình",
        "poster_key": "/movies/poster-3.png",
        "backdrop_key": "/movies/hero-backdrop.png",
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
                    ("Two-Face (1)", "Harvey Dent đổ vỡ."),
                    ("Two-Face (2)", "Batman đối đầu người bạn cũ."),
                    ("Joker's Favor", "Charlie và kế hoạch của Joker."),
                ],
            },
        ],
    },
]


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
