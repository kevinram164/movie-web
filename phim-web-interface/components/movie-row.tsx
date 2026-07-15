"use client"

import { ChevronLeft, ChevronRight } from "lucide-react"
import { useRef } from "react"
import { MovieCard } from "@/components/movie-card"
import type { SeriesCard } from "@/lib/api"

export function MovieRow({ title, movies }: { title: string; movies: SeriesCard[] }) {
  const scroller = useRef<HTMLDivElement>(null)

  if (!movies.length) return null

  const scroll = (dir: -1 | 1) => {
    const el = scroller.current
    if (!el) return
    el.scrollBy({ left: dir * Math.min(el.clientWidth * 0.8, 600), behavior: "smooth" })
  }

  return (
    <section className="relative mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-xl font-bold sm:text-2xl">{title}</h2>
        <div className="flex gap-1">
          <button
            type="button"
            aria-label="Cuộn trái"
            onClick={() => scroll(-1)}
            className="rounded-full border border-border p-2 text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-4" />
          </button>
          <button
            type="button"
            aria-label="Cuộn phải"
            onClick={() => scroll(1)}
            className="rounded-full border border-border p-2 text-muted-foreground hover:text-foreground"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
      <div
        ref={scroller}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-none [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {movies.map((m) => (
          <MovieCard key={m.id} movie={m} />
        ))}
      </div>
    </section>
  )
}
