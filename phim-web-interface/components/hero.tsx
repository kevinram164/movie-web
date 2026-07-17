"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Info, Play, Star } from "lucide-react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { SeriesCard } from "@/lib/api"

export function Hero({ items }: { items: SeriesCard[] }) {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (items.length < 2 || paused) return undefined
    const timer = window.setInterval(() => {
      setActive((index) => (index + 1) % items.length)
    }, 6500)
    return () => window.clearInterval(timer)
  }, [items.length, paused])

  useEffect(() => {
    if (active >= items.length) setActive(0)
  }, [active, items.length])

  if (!items.length) {
    return (
      <section className="relative flex min-h-[50vh] items-end bg-secondary px-4 pb-16 pt-28">
        <p className="text-muted-foreground">Đang tải catalog…</p>
      </section>
    )
  }

  const featured = items[active]
  const move = (direction: number) => {
    setActive((index) => (index + direction + items.length) % items.length)
  }

  return (
    <section
      className="relative min-h-[88vh] w-full overflow-hidden"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {items.map((item, index) => (
        <img
          key={item.slug}
          src={item.backdrop_url || item.poster_url || "/placeholder.svg"}
          alt={index === active ? `Ảnh nền ${item.title}` : ""}
          aria-hidden={index !== active}
          className={cn(
            "absolute inset-0 size-full object-cover transition-all duration-1000 ease-in-out",
            index === active ? "scale-100 opacity-100" : "scale-105 opacity-0",
          )}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/70 to-background/30" />
      <div className="absolute inset-0 bg-gradient-to-r from-background/90 via-background/40 to-transparent" />

      <div className="relative mx-auto flex min-h-[88vh] max-w-7xl flex-col justify-end px-4 pb-16 pt-28 sm:px-6 lg:px-8 lg:pb-24">
        <div key={featured.slug} className="max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-700">
          <span className="inline-flex items-center rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary">
            {featured.franchise} · Animation series
          </span>

          <h1 className="mt-4 text-pretty font-display text-4xl font-extrabold leading-tight sm:text-5xl lg:text-6xl">
            {featured.title}
          </h1>
          {featured.english_title && (
            <p className="mt-1 text-lg text-muted-foreground">{featured.english_title}</p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1 font-semibold text-foreground">
              <Star className="size-4 fill-primary text-primary" />
              {featured.rating}
            </span>
            <span>{featured.year_start}</span>
            <span className="rounded border border-border px-1.5 py-0.5 text-xs">T13</span>
            <span>{featured.episode_count} tập</span>
            <span className="rounded bg-primary/15 px-1.5 py-0.5 text-xs font-medium text-primary">HD</span>
          </div>

          <p className="mt-4 max-w-xl text-pretty leading-relaxed text-muted-foreground">
            {featured.description}
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link
              href={`/series/${featured.slug}`}
              className={cn(buttonVariants({ size: "lg" }), "gap-2 font-semibold")}
            >
              <Play className="size-5 fill-current" />
              Xem series
            </Link>
            <Link
              href={`/series/${featured.slug}`}
              className={cn(buttonVariants({ size: "lg", variant: "secondary" }), "gap-2 font-semibold")}
            >
              <Info className="size-5" />
              Chi tiết
            </Link>
          </div>
        </div>

        {items.length > 1 && (
          <div className="mt-8 flex items-center gap-3">
            <button
              type="button"
              onClick={() => move(-1)}
              aria-label="Phim trước"
              className="grid size-10 place-items-center rounded-full border border-white/20 bg-black/35 backdrop-blur transition hover:bg-black/60"
            >
              <ChevronLeft className="size-5" />
            </button>
            <div className="flex items-center gap-2" aria-label="Chọn phim nổi bật">
              {items.map((item, index) => (
                <button
                  key={item.slug}
                  type="button"
                  onClick={() => setActive(index)}
                  aria-label={`Hiển thị ${item.title}`}
                  aria-current={index === active}
                  className={cn(
                    "h-1.5 rounded-full transition-all duration-500",
                    index === active ? "w-9 bg-primary" : "w-4 bg-white/40 hover:bg-white/70",
                  )}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={() => move(1)}
              aria-label="Phim tiếp theo"
              className="grid size-10 place-items-center rounded-full border border-white/20 bg-black/35 backdrop-blur transition hover:bg-black/60"
            >
              <ChevronRight className="size-5" />
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
