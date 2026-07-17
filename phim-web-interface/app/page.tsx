"use client"

import { useEffect, useState } from "react"
import { SiteHeader } from "@/components/site-header"
import { Hero } from "@/components/hero"
import { GenreBar } from "@/components/genre-bar"
import { MovieRow } from "@/components/movie-row"
import { SiteFooter } from "@/components/site-footer"
import { fetchHome, type HomeData } from "@/lib/api"

export default function Page() {
  const [data, setData] = useState<HomeData | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const home = await fetchHome()
        if (!cancelled) setData(home)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không tải được catalog")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <Hero items={data?.rows[0]?.items ?? (data?.featured ? [data.featured] : [])} />
      <GenreBar />
      {error && (
        <p className="mx-auto max-w-7xl px-4 py-4 text-sm text-destructive sm:px-6 lg:px-8">{error}</p>
      )}
      {!data && !error && (
        <p className="mx-auto max-w-7xl px-4 py-8 text-muted-foreground sm:px-6 lg:px-8">Đang tải series…</p>
      )}
      {data?.rows.map((row) => (
        <MovieRow key={row.title} title={row.title} movies={row.items} />
      ))}
      <SiteFooter />
    </main>
  )
}
