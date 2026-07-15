"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Search, Bell, Menu, Play, X } from "lucide-react"
import { Button } from "@/components/ui/button"

const navItems = [
  { label: "Trang chủ", href: "/" },
  { label: "X-Men", href: "/series/x-men-animated" },
  { label: "Spider-Man", href: "/series/spiderman-animated" },
  { label: "Batman", href: "/series/batman-animated" },
]

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled ? "bg-background/90 backdrop-blur-md border-b border-border" : "bg-gradient-to-b from-background/90 to-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Play className="size-4 fill-current" />
          </span>
          <span className="font-display text-xl font-extrabold tracking-tight">
            Cine<span className="text-primary">Home</span>
          </span>
        </Link>

        <nav className="ml-6 hidden items-center gap-1 lg:flex">
          {navItems.map((item, i) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-foreground ${
                i === 0 ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <div className="hidden items-center rounded-full border border-border bg-secondary/60 px-3 py-1.5 md:flex">
            <Search className="size-4 text-muted-foreground" />
            <input
              type="search"
              placeholder="Tìm series…"
              aria-label="Tìm kiếm"
              className="w-40 bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground lg:w-52"
            />
          </div>
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Tìm kiếm">
            <Search className="size-5" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Thông báo">
            <Bell className="size-5" />
          </Button>
          <Button className="hidden font-semibold sm:inline-flex" disabled>
            Đăng nhập
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Mở menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
        </div>
      </div>

      {menuOpen && (
        <nav className="border-t border-border bg-background/95 px-4 py-3 backdrop-blur-md lg:hidden">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  )
}
