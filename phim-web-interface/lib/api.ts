export type SeriesCard = {
  id: number
  slug: string
  title: string
  english_title: string
  year_start: number
  franchise: string
  genre: string
  rating: string
  poster_url: string
  backdrop_url: string
  episode_count: number
}

export type Episode = {
  id: number
  number: number
  title: string
  description: string
  duration_minutes: number
  hls_key: string
  poster_url: string
  season_number: number
  series_slug: string
  series_title: string
}

export type Season = {
  id: number
  number: number
  title: string
  episodes: Episode[]
}

export type SeriesDetail = SeriesCard & {
  description: string
  seasons: Season[]
}

export type HomeData = {
  featured: SeriesDetail | null
  rows: { title: string; items: SeriesCard[] }[]
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "")

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 15 },
  })
  if (!res.ok) {
    throw new Error((await res.text()) || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function fetchHome() {
  return request<HomeData>("/api/home")
}

export function fetchSeries(slug: string) {
  return request<SeriesDetail>(`/api/series/${slug}`)
}

export function fetchEpisode(id: number | string) {
  return request<Episode>(`/api/episodes/${id}`)
}

export function fetchEpisodeStream(id: number | string) {
  return request<{ hls_url: string; expires_in: number; episode_id: number }>(
    `/api/episodes/${id}/stream`,
  )
}

export const genreCategories = [
  "Tất cả",
  "Hoạt hình",
  "Hành động",
  "X-Men",
  "Spider-Man",
  "Batman",
]
