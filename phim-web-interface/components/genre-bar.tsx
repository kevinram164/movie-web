"use client"

import { genreCategories } from "@/lib/api"

export function GenreBar() {
  return (
    <div className="sticky top-16 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 py-3 [scrollbar-width:none] sm:px-6 lg:px-8 [&::-webkit-scrollbar]:hidden">
        {genreCategories.map((g, i) => (
          <span
            key={g}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold sm:text-sm ${
              i === 0
                ? "border-primary bg-primary/15 text-foreground"
                : "border-border text-muted-foreground"
            }`}
          >
            {g}
          </span>
        ))}
      </div>
    </div>
  )
}
