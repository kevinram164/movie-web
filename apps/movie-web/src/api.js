const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

async function request(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export function listMovies(q = "") {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return request(`/api/movies${qs}`);
}

export function getMovie(id) {
  return request(`/api/movies/${id}`);
}

export function getStream(id) {
  return request(`/api/movies/${id}/stream`);
}
