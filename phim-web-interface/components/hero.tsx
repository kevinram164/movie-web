"use client"

import Link from "next/link"
import { Play, Info, Star, Plus } from "lucide-react"
import { Button, buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { SeriesDetail } from "@/lib/api"

export function Hero({ featured }: { featured: SeriesDetail | null }) {
  if (!featured) {
    return (
      <section className="relative flex min-h-[50vh] items-end bg-secondary px-4 pb-16 pt-28">
        <p className="text-muted-foreground">Đang tải catalog…</p>
      </section>
    )
  }

  return (
    <section className="relative min-h-[88vh] w-full overflow-hidden">
      <img
        src={featured.backdrop_url || featured.poster_url || "/placeholder.svg"}
        alt={`Ảnh nền ${featured.title}`}
        className="absolute inset-0 size-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/70 to-background/30" />
      <div className="absolute inset-0 bg-gradient-to-r from-background/90 via-background/40 to-transparent" />

      <div className="relative mx-auto flex min-h-[88vh] max-w-7xl flex-col justify-end px-4 pb-16 pt-28 sm:px-6 lg:px-8 lg:pb-24">
        <div className="max-w-2xl">
          <span className="inline-flex items-center rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-primary">
            Animation series
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
            <Button size="lg" variant="outline" className="gap-2 bg-transparent font-semibold" disabled>
              <Plus className="size-5" />
              Danh sách
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}
