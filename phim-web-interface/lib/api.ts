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
  status?: string
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

export type UploadInit = {
  episode_id: number
  raw_key: string
  upload_url: string
  subtitle_raw_key: string
  subtitle_upload_url: string
  expires_in: number
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "")

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData
  const headers: HeadersInit = {
    ...(!isForm && init?.body ? { "Content-Type": "application/json" } : {}),
    ...init?.headers,
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  })
  if (!res.ok) {
    throw new Error((await res.text()) || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function fetchHome() {
  return request<HomeData>("/api/home")
}

export function fetchSeriesList() {
  return request<SeriesCard[]>("/api/series")
}

export function fetchSeries(slug: string) {
  return request<SeriesDetail>(`/api/series/${slug}`)
}

export function fetchEpisode(id: number | string) {
  return request<Episode>(`/api/episodes/${id}`)
}

export function fetchEpisodeStream(id: number | string) {
  return request<{
    hls_url: string
    subtitle_url?: string
    expires_in: number
    episode_id: number
  }>(`/api/episodes/${id}/stream`)
}

export function createEpisode(
  slug: string,
  seasonNumber: number,
  body: { title: string; number: number; description?: string; duration_minutes?: number },
) {
  return request<Episode>(`/api/series/${slug}/seasons/${seasonNumber}/episodes`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function uploadInit(episodeId: number, filename: string, withSubtitle: boolean) {
  const q = new URLSearchParams({
    filename,
    with_subtitle: String(withSubtitle),
  })
  return request<UploadInit>(`/api/episodes/${episodeId}/upload-init?${q}`, {
    method: "POST",
  })
}

export function uploadComplete(episodeId: number) {
  return request<Episode>(`/api/episodes/${episodeId}/upload-complete`, {
    method: "POST",
  })
}

/** Upload lớn: PUT thẳng MinIO (tránh proxy multipart qua Next → 500). */
export async function putToPresigned(url: string, file: File) {
  const res = await fetch(url, {
    method: "PUT",
    body: file,
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
  })
  if (!res.ok) {
    throw new Error(`Upload MinIO thất bại: HTTP ${res.status}`)
  }
}

export async function uploadViaPresign(
  episodeId: number,
  video: File,
  subtitle?: File | null,
) {
  const init = await uploadInit(episodeId, video.name, Boolean(subtitle))
  await putToPresigned(init.upload_url, video)
  if (subtitle && init.subtitle_upload_url) {
    await putToPresigned(init.subtitle_upload_url, subtitle)
  }
  return uploadComplete(episodeId)
}

export const genreCategories = [
  "Tất cả",
  "Hoạt hình",
  "Hành động",
  "X-Men",
  "Spider-Man",
  "Batman",
]
