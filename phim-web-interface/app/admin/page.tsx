"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { ArrowLeft, Upload } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import {
  createEpisode,
  fetchEpisode,
  fetchSeries,
  fetchSeriesList,
  uploadViaPresign,
  type Episode,
  type SeriesCard,
  type SeriesDetail,
} from "@/lib/api"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export default function AdminUploadPage() {
  const [seriesList, setSeriesList] = useState<SeriesCard[]>([])
  const [slug, setSlug] = useState("")
  const [detail, setDetail] = useState<SeriesDetail | null>(null)
  const [seasonNumber, setSeasonNumber] = useState(1)
  const [episodeId, setEpisodeId] = useState<number | "">("")
  const [newTitle, setNewTitle] = useState("")
  const [newNumber, setNewNumber] = useState(1)
  const [video, setVideo] = useState<File | null>(null)
  const [subtitle, setSubtitle] = useState<File | null>(null)
  const [log, setLog] = useState("")
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState("")

  useEffect(() => {
    fetchSeriesList()
      .then((items) => {
        setSeriesList(items)
        setSlug((prev) => prev || items[0]?.slug || "")
      })
      .catch((err) => setLog(err instanceof Error ? err.message : String(err)))
  }, [])

  const reloadDetail = useCallback(async (s: string) => {
    if (!s) return
    const data = await fetchSeries(s)
    setDetail(data)
    if (data.seasons[0]) setSeasonNumber(data.seasons[0].number)
  }, [])

  useEffect(() => {
    if (!slug) return
    reloadDetail(slug).catch((err) => setLog(err instanceof Error ? err.message : String(err)))
  }, [slug, reloadDetail])

  const season = detail?.seasons.find((s) => s.number === seasonNumber)
  const selectedEp: Episode | undefined = season?.episodes.find((e) => e.id === episodeId)

  useEffect(() => {
    if (!episodeId || typeof episodeId !== "number") return
    if (!["PROCESSING", "UPLOADING"].includes(selectedEp?.status || "")) return
    const t = setInterval(() => {
      fetchEpisode(episodeId)
        .then((ep) => {
          setStatus(ep.status || "")
          if (ep.status === "READY" || ep.status === "FAILED") {
            reloadDetail(slug)
          }
        })
        .catch(() => undefined)
    }, 4000)
    return () => clearInterval(t)
  }, [episodeId, selectedEp?.status, reloadDetail, slug])

  async function onCreateEpisode() {
    if (!slug || !newTitle.trim()) return
    setBusy(true)
    setLog("")
    try {
      const ep = await createEpisode(slug, seasonNumber, {
        title: newTitle.trim(),
        number: newNumber,
      })
      await reloadDetail(slug)
      setEpisodeId(ep.id)
      setLog(`Đã tạo episode #${ep.id} — ${ep.title}`)
    } catch (err) {
      setLog(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onUpload() {
    if (!episodeId || typeof episodeId !== "number" || !video) {
      setLog("Chọn episode và file video (.mp4)")
      return
    }
    setBusy(true)
    setLog("upload-init → PUT MinIO (presigned) → upload-complete …")
    setStatus("UPLOADING")
    try {
      const ep = await uploadViaPresign(episodeId, video, subtitle)
      setStatus(ep.status || "PROCESSING")
      setLog(
        `Xong upload. Status: ${ep.status}. media-worker đang convert HLS — đợi READY rồi xem tập.`,
      )
      await reloadDetail(slug)
    } catch (err) {
      setLog(err instanceof Error ? err.message : String(err))
      setStatus("FAILED")
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <div className="mx-auto max-w-3xl px-4 pb-16 pt-24 sm:px-6">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Catalog
        </Link>

        <h1 className="font-display text-3xl font-extrabold">Upload & convert</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Browser PUT thẳng MinIO (presigned) → Redis → media-worker ffmpeg HLS. Không proxy file lớn qua
          Next.js.
        </p>

        <div className="mt-8 space-y-6">
          <label className="block space-y-2 text-sm">
            <span className="font-medium">Series</span>
            <select
              className="w-full rounded-md border border-border bg-secondary/40 px-3 py-2"
              value={slug}
              onChange={(e) => {
                setSlug(e.target.value)
                setEpisodeId("")
              }}
            >
              {seriesList.map((s) => (
                <option key={s.slug} value={s.slug}>
                  {s.title}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span className="font-medium">Season</span>
            <select
              className="w-full rounded-md border border-border bg-secondary/40 px-3 py-2"
              value={seasonNumber}
              onChange={(e) => {
                setSeasonNumber(Number(e.target.value))
                setEpisodeId("")
              }}
            >
              {(detail?.seasons || [{ number: 1, title: "Season 1", id: 0, episodes: [] }]).map(
                (s) => (
                  <option key={s.number} value={s.number}>
                    {s.title || `Season ${s.number}`}
                  </option>
                ),
              )}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span className="font-medium">Episode có sẵn</span>
            <select
              className="w-full rounded-md border border-border bg-secondary/40 px-3 py-2"
              value={episodeId}
              onChange={(e) => setEpisodeId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">— chọn tập —</option>
              {season?.episodes.map((ep) => (
                <option key={ep.id} value={ep.id}>
                  E{ep.number} — {ep.title} [{ep.status || "PENDING"}]
                </option>
              ))}
            </select>
            {selectedEp && (
              <p className="text-xs text-muted-foreground">
                Status: <span className="text-primary">{status || selectedEp.status}</span> ·{" "}
                {selectedEp.hls_key}
              </p>
            )}
          </label>

          <div className="rounded-lg border border-border p-4">
            <p className="mb-3 text-sm font-medium">Hoặc tạo tập mới</p>
            <div className="grid gap-3 sm:grid-cols-[80px_1fr_auto]">
              <input
                type="number"
                min={1}
                className="rounded-md border border-border bg-secondary/40 px-3 py-2 text-sm"
                value={newNumber}
                onChange={(e) => setNewNumber(Number(e.target.value))}
                aria-label="Số tập"
              />
              <input
                type="text"
                placeholder="Tiêu đề tập"
                className="rounded-md border border-border bg-secondary/40 px-3 py-2 text-sm"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
              />
              <button
                type="button"
                disabled={busy}
                onClick={onCreateEpisode}
                className={cn(buttonVariants({ variant: "secondary" }), "font-semibold")}
              >
                Tạo
              </button>
            </div>
          </div>

          <label className="block space-y-2 text-sm">
            <span className="font-medium">Video (.mp4)</span>
            <input
              type="file"
              accept="video/mp4,video/*,.mp4,.mkv"
              onChange={(e) => setVideo(e.target.files?.[0] || null)}
              className="block w-full text-sm"
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span className="font-medium">Phụ đề (.srt) — tuỳ chọn</span>
            <input
              type="file"
              accept=".srt,text/plain"
              onChange={(e) => setSubtitle(e.target.files?.[0] || null)}
              className="block w-full text-sm"
            />
          </label>

          <button
            type="button"
            disabled={busy || !episodeId || !video}
            onClick={onUpload}
            className={cn(buttonVariants({ size: "lg" }), "inline-flex gap-2 font-semibold")}
          >
            <Upload className="size-5" />
            {busy ? "Đang xử lý…" : "Upload + convert"}
          </button>

          {log && (
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border border-border bg-secondary/30 p-3 text-xs text-muted-foreground">
              {log}
            </pre>
          )}
        </div>
      </div>
      <SiteFooter />
    </main>
  )
}
