"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { Play, ArrowLeft, Star } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { fetchSeries, type SeriesDetail } from "@/lib/api"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export default function SeriesPage() {
  const params = useParams<{ slug: string }>()
  const [series, setSeries] = useState<SeriesDetail | null>(null)
  const [error, setError] = useState("")
  const [seasonIdx, setSeasonIdx] = useState(0)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await fetchSeries(params.slug)
        if (!cancelled) setSeries(data)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không tải được series")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [params.slug])

  const season = series?.seasons[seasonIdx]
  const firstEp = season?.episodes[0]

  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-4 pb-16 pt-24 sm:px-6 lg:px-8">
        <Link href="/" className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
          Catalog
        </Link>

        {error && <p className="text-destructive">{error}</p>}
        {!series && !error && <p className="text-muted-foreground">Đang tải…</p>}

        {series && (
          <>
            <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
              <img
                src={series.poster_url || "/placeholder.svg"}
                alt={series.title}
                className="aspect-[2/3] w-full max-w-[240px] rounded-lg object-cover ring-1 ring-border"
              />
              <div>
                <h1 className="font-display text-3xl font-extrabold sm:text-4xl">{series.title}</h1>
                {series.english_title && (
                  <p className="mt-1 text-muted-foreground">{series.english_title}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-3 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1 text-foreground">
                    <Star className="size-4 fill-primary text-primary" />
                    {series.rating}
                  </span>
                  <span>{series.year_start}</span>
                  <span>{series.genre}</span>
                  <span>{series.episode_count} tập</span>
                </div>
                <p className="mt-4 max-w-2xl leading-relaxed text-muted-foreground">{series.description}</p>
                {firstEp && (
                  <Link
                    href={`/watch/${firstEp.id}`}
                    className={cn(buttonVariants({ size: "lg" }), "mt-6 inline-flex gap-2 font-semibold")}
                  >
                    <Play className="size-5 fill-current" />
                    Phát tập 1
                  </Link>
                )}
              </div>
            </div>

            <div className="mt-10">
              <div className="mb-4 flex flex-wrap gap-2">
                {series.seasons.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setSeasonIdx(i)}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                      i === seasonIdx
                        ? "border-primary bg-primary/15 text-foreground"
                        : "border-border text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {s.title || `Season ${s.number}`}
                  </button>
                ))}
              </div>

              <ul className="divide-y divide-border rounded-lg border border-border">
                {season?.episodes.map((ep) => (
                  <li key={ep.id}>
                    <Link
                      href={`/watch/${ep.id}`}
                      className="flex items-start gap-4 p-4 transition-colors hover:bg-secondary/50"
                    >
                      <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-sm font-bold text-primary">
                        {ep.number}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold">{ep.title}</h3>
                          <span className="text-xs text-muted-foreground">{ep.duration_minutes}p</span>
                          {ep.status && ep.status !== "READY" && ep.status !== "PENDING" && (
                            <span className="text-xs text-primary">{ep.status}</span>
                          )}
                        </div>
                        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{ep.description}</p>
                      </div>
                      <Play className="mt-2 size-5 shrink-0 text-muted-foreground" />
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                HLS path MinIO:{" "}
                <code className="text-primary">
                  {series.slug}/sXXeYY/master.m3u8
                </code>
              </p>
            </div>
          </>
        )}
      </div>
      <SiteFooter />
    </main>
  )
}
