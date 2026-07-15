"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import Hls from "hls.js"
import { ArrowLeft } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { fetchEpisode, fetchEpisodeStream, type Episode } from "@/lib/api"

export default function WatchPage() {
  const params = useParams<{ episodeId: string }>()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [episode, setEpisode] = useState<Episode | null>(null)
  const [hlsUrl, setHlsUrl] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [ep, stream] = await Promise.all([
          fetchEpisode(params.episodeId),
          fetchEpisodeStream(params.episodeId),
        ])
        if (cancelled) return
        setEpisode(ep)
        setHlsUrl(stream.hls_url)
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
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl
    }

    return () => {
      hls?.destroy()
    }
  }, [hlsUrl])

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
          <video ref={videoRef} className="aspect-video w-full" controls playsInline poster={episode?.poster_url} />
        </div>

        {episode && (
          <p className="mt-3 text-xs text-muted-foreground">
            Nguồn: Upload HLS lên MinIO key{" "}
            <code className="text-primary">{episode.hls_key}</code>
          </p>
        )}
      </div>
    </main>
  )
}
