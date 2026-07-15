"use client"

import Link from "next/link"
import { Play, Plus, Star } from "lucide-react"
import type { SeriesCard } from "@/lib/api"

export function MovieCard({ movie }: { movie: SeriesCard }) {
  return (
    <article className="group relative w-40 shrink-0 sm:w-44 lg:w-48">
      <Link href={`/series/${movie.slug}`} className="block">
        <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-secondary ring-1 ring-border transition-transform duration-300 group-hover:-translate-y-1 group-hover:ring-primary/60">
          <img
            src={movie.poster_url || "/placeholder.svg"}
            alt={`Áp phích ${movie.title}`}
            className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
          />

          <div className="absolute left-2 top-2 flex gap-1.5">
            <span className="rounded bg-background/80 px-1.5 py-0.5 text-[10px] font-bold text-foreground backdrop-blur">
              HD
            </span>
            <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-bold text-primary-foreground">
              SERIES
            </span>
          </div>

          <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-background/95 via-background/20 to-transparent p-3 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
            <div className="flex items-center gap-2">
              <span className="flex size-9 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Play className="size-4 fill-current" />
              </span>
              <span className="flex size-9 items-center justify-center rounded-full border border-border bg-background/70 text-foreground backdrop-blur">
                <Plus className="size-4" />
              </span>
            </div>
          </div>
        </div>

        <div className="mt-2.5">
          <h3 className="truncate text-sm font-semibold text-foreground">{movie.title}</h3>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-0.5">
              <Star className="size-3 fill-primary text-primary" />
              {movie.rating}
            </span>
            <span>•</span>
            <span>{movie.year_start}</span>
            <span>•</span>
            <span className="truncate">{movie.episode_count} tập</span>
          </div>
        </div>
      </Link>
    </article>
  )
}
