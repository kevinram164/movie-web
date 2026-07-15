import { Play } from "lucide-react"

const columns = [
  { title: "Khám phá", links: ["Phim lẻ", "Phim bộ", "Phim chiếu rạp", "Sắp chiếu"] },
  { title: "Thể loại", links: ["Hành động", "Tình cảm", "Kinh dị", "Hoạt hình"] },
  { title: "Hỗ trợ", links: ["Câu hỏi thường gặp", "Liên hệ", "Điều khoản", "Bảo mật"] },
]

export function SiteFooter() {
  return (
    <footer className="mt-10 border-t border-border bg-card/40">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-4 py-12 sm:px-6 md:grid-cols-4 lg:px-8">
        <div className="col-span-2 md:col-span-1">
          <a href="/" className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Play className="size-4 fill-current" />
            </span>
            <span className="font-display text-xl font-extrabold tracking-tight">
              Cine<span className="text-primary">Home</span>
            </span>
          </a>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Nền tảng xem phim trực tuyến chất lượng cao. Hàng ngàn bộ phim bom tấn, cập nhật mỗi ngày.
          </p>
        </div>

        {columns.map((col) => (
          <div key={col.title}>
            <h3 className="text-sm font-semibold text-foreground">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((link) => (
                <li key={link}>
                  <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-primary">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-5 text-center text-xs text-muted-foreground sm:px-6 lg:px-8">
          © {new Date().getFullYear()} CineViet. Chỉ dành cho mục đích trình diễn giao diện.
        </div>
      </div>
    </footer>
  )
}
