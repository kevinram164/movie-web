"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import Hls from "hls.js"
import { ArrowLeft, SkipForward } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { fetchEpisode, fetchEpisodeStream, fetchSeries, type Episode } from "@/lib/api"

export default function WatchPage() {
  const params = useParams<{ episodeId: string }>()
  const router = useRouter()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [episode, setEpisode] = useState<Episode | null>(null)
  const [nextEpisode, setNextEpisode] = useState<Episode | null>(null)
  const [hlsUrl, setHlsUrl] = useState("")
  const [subtitleUrl, setSubtitleUrl] = useState("")
  const [error, setError] = useState("")
  const [autoNext, setAutoNext] = useState(true)
  const [countdown, setCountdown] = useState<number | null>(null)

  useEffect(() => {
    const saved = window.localStorage.getItem("cinehome:auto-next")
    if (saved !== null) setAutoNext(saved === "true")
  }, [])

  function updateAutoNext(enabled: boolean) {
    setAutoNext(enabled)
    window.localStorage.setItem("cinehome:auto-next", String(enabled))
    if (!enabled) setCountdown(null)
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setCountdown(null)
        setError("")
        setNextEpisode(null)
        const [ep, stream] = await Promise.all([
          fetchEpisode(params.episodeId),
          fetchEpisodeStream(params.episodeId),
        ])
        if (cancelled) return
        setEpisode(ep)
        setHlsUrl(stream.hls_url)
        setSubtitleUrl(stream.subtitle_url || "")
        const detail = await fetchSeries(ep.series_slug)
        if (cancelled) return
        const episodes = detail.seasons
          .slice()
          .sort((a, b) => a.number - b.number)
          .flatMap((season) => season.episodes.slice().sort((a, b) => a.number - b.number))
        const currentIdx = episodes.findIndex((item) => item.id === ep.id)
        setNextEpisode(currentIdx >= 0 ? episodes[currentIdx + 1] || null : null)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không phát được tập")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [params.episodeId])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !hlsUrl) return undefined

    let hls: Hls | undefined
    if (Hls.isSupported()) {
      hls = new Hls({ enableWorker: true })
      hls.loadSource(hlsUrl)
      hls.attachMedia(video)
      // Dùng <track> VTT riêng; tắt subtitle HLS để tránh hiện 2 lần
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (hls) {
          hls.subtitleTrack = -1
          hls.subtitleDisplay = false
        }
      })
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari: phụ đề lấy từ EXT-X-MEDIA trong master.m3u8 (nếu worker đã inject)
      video.src = hlsUrl
    }

    return () => {
      hls?.destroy()
    }
  }, [hlsUrl])

  // External VTT (nội dung cũ chưa có SUBTITLES trong master.m3u8)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !subtitleUrl) return undefined

    const existing = video.querySelectorAll('track[data-cinehome-sub="1"]')
    existing.forEach((el) => el.remove())

    const track = document.createElement("track")
    track.kind = "subtitles"
    track.label = "Tiếng Việt"
    track.srclang = "vi"
    track.src = subtitleUrl
    track.default = true
    track.dataset.cinehomeSub = "1"
    video.appendChild(track)

    const enable = () => {
      const textTracks = video.textTracks
      for (let i = 0; i < textTracks.length; i++) {
        const t = textTracks[i]
        if (t.language === "vi" || t.label === "Tiếng Việt") {
          t.mode = "showing"
        }
      }
    }
    video.addEventListener("loadedmetadata", enable)
    enable()

    return () => {
      video.removeEventListener("loadedmetadata", enable)
      track.remove()
    }
  }, [subtitleUrl, hlsUrl])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return undefined
    const handleEnded = () => {
      if (autoNext && nextEpisode) setCountdown(5)
    }
    video.addEventListener("ended", handleEnded)
    return () => video.removeEventListener("ended", handleEnded)
  }, [autoNext, nextEpisode])

  useEffect(() => {
    if (countdown === null || !nextEpisode) return undefined
    if (countdown <= 0) {
      setCountdown(null)
      router.push(`/watch/${nextEpisode.id}`)
      return undefined
    }
    const timer = window.setTimeout(() => setCountdown((value) => (value === null ? null : value - 1)), 1000)
    return () => window.clearTimeout(timer)
  }, [countdown, nextEpisode, router])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <div className="mx-auto max-w-5xl px-4 pb-16 pt-24 sm:px-6 lg:px-8">
        {episode && (
          <Link
            href={`/series/${episode.series_slug}`}
            className="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            {episode.series_title}
          </Link>
        )}

        {error && <p className="mb-4 text-destructive">{error}</p>}

        {episode && (
          <div className="mb-4">
            <h1 className="font-display text-2xl font-bold sm:text-3xl">
              S{episode.season_number}E{episode.number} · {episode.title}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{episode.description}</p>
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-border bg-black">
          <video
            ref={videoRef}
            className="aspect-video w-full"
            controls
            playsInline
            crossOrigin="anonymous"
            poster={episode?.poster_url}
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={autoNext}
              onChange={(event) => updateAutoNext(event.target.checked)}
              className="size-4 accent-primary"
            />
            Tự động chuyển tập
          </label>
          {nextEpisode && (
            <button
              type="button"
              onClick={() => {
                setCountdown(null)
                router.push(`/watch/${nextEpisode.id}`)
              }}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-secondary"
            >
              Tập tiếp theo: S{nextEpisode.season_number}E{nextEpisode.number}
              <SkipForward className="size-4" />
            </button>
          )}
        </div>

        {countdown !== null && nextEpisode && (
          <div className="mt-4 flex items-center justify-between gap-3 rounded-lg border border-primary/40 bg-primary/10 p-4">
            <p className="text-sm">
              Chuyển sang <strong>{nextEpisode.title}</strong> sau {countdown} giây…
            </p>
            <button
              type="button"
              onClick={() => setCountdown(null)}
              className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-background"
            >
              Hủy
            </button>
          </div>
        )}

        {episode && (
          <p className="mt-3 text-xs text-muted-foreground">
            Nguồn: Upload HLS lên MinIO key{" "}
            <code className="text-primary">{episode.hls_key}</code>
            {subtitleUrl ? " · Phụ đề: Tiếng Việt" : ""}
          </p>
        )}
      </div>
    </main>
  )
}
