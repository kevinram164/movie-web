import { Link, Route, Routes, useParams } from "react-router-dom";
import { useDeferredValue, useEffect, useState } from "react";
import { getMovie, getStream, listMovies } from "./api";
import HlsPlayer from "./HlsPlayer";

function Shell({ children }) {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          CineHome
        </Link>
        <span className="topbar-note">Xem phim tại nhà · OCP</span>
      </header>
      {children}
    </div>
  );
}

function Home() {
  const [q, setQ] = useState("");
  const deferredQ = useDeferredValue(q);
  const [movies, setMovies] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await listMovies(deferredQ);
        if (!cancelled) setMovies(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Không tải được danh sách phim");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [deferredQ]);

  const featured = movies[0];

  return (
    <Shell>
      <section className="hero">
        <div className="hero-veil" />
        <div className="hero-copy">
          <p className="hero-kicker">Thư viện nhà bạn</p>
          <h1 className="hero-brand">CineHome</h1>
          <p className="hero-lead">
            Catalog phim trên OpenShift — stream HLS từ MinIO.
          </p>
          {featured && (
            <Link className="cta" to={`/watch/${featured.id}`}>
              Xem {featured.title}
            </Link>
          )}
        </div>
      </section>

      <section className="catalog">
        <div className="catalog-head">
          <h2>Danh sách phim</h2>
          <input
            className="search"
            placeholder="Tìm phim…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        {loading && <p className="muted">Đang tải…</p>}
        {error && <p className="error">{error}</p>}
        <div className="grid">
          {movies.map((m) => (
            <Link key={m.id} to={`/watch/${m.id}`} className="poster-link">
              <article className="poster">
                <div
                  className="poster-art"
                  style={
                    m.poster_url
                      ? { backgroundImage: `url(${m.poster_url})` }
                      : undefined
                  }
                />
                <div className="poster-meta">
                  <h3>{m.title}</h3>
                  <p>
                    {m.year || "—"} · {m.genre || "Khác"}
                    {m.duration_minutes ? ` · ${m.duration_minutes}p` : ""}
                  </p>
                </div>
              </article>
            </Link>
          ))}
        </div>
      </section>
    </Shell>
  );
}

function Watch() {
  const { id } = useParams();
  const [movie, setMovie] = useState(null);
  const [hlsUrl, setHlsUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, stream] = await Promise.all([getMovie(id), getStream(id)]);
        if (cancelled) return;
        setMovie(m);
        setHlsUrl(stream.hls_url);
      } catch (err) {
        if (!cancelled) setError(err.message || "Không phát được phim");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <Shell>
      <section className="watch">
        <Link to="/" className="back">
          ← Catalog
        </Link>
        {error && <p className="error">{error}</p>}
        {movie && (
          <>
            <div className="watch-head">
              <h1>{movie.title}</h1>
              <p>
                {movie.year} · {movie.genre} · {movie.duration_minutes} phút
              </p>
              <p className="desc">{movie.description}</p>
            </div>
            <HlsPlayer src={hlsUrl} poster={movie.poster_url} />
            <p className="muted stream-hint">
              Nguồn HLS: Upload <code>master.m3u8</code> + segments vào MinIO
              bucket <code>movies</code> theo key <code>{movie.hls_key}</code>
            </p>
          </>
        )}
      </section>
    </Shell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/watch/:id" element={<Watch />} />
    </Routes>
  );
}
