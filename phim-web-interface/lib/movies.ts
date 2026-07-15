export type Movie = {
  id: string
  title: string
  poster: string
  year: number
  rating: number
  duration: string
  genres: string[]
  quality: "4K" | "HD" | "CAM"
  isNew?: boolean
}

export const featured = {
  id: "the-last-horizon",
  title: "Chân Trời Cuối Cùng",
  englishTitle: "The Last Horizon",
  backdrop: "/movies/hero-backdrop.png",
  year: 2025,
  rating: 8.7,
  duration: "2h 18m",
  ageRating: "T16",
  genres: ["Khoa học viễn tưởng", "Phiêu lưu", "Chính kịch"],
  description:
    "Khi Trái Đất không còn là nơi trú ẩn an toàn, một phi hành gia đơn độc dấn thân vào hành trình xuyên qua hành tinh đỏ xa xôi để tìm kiếm hy vọng cuối cùng cho nhân loại.",
}

const posters = [
  "/movies/poster-1.png",
  "/movies/poster-2.png",
  "/movies/poster-3.png",
  "/movies/poster-4.png",
  "/movies/poster-5.png",
  "/movies/poster-6.png",
  "/movies/poster-7.png",
  "/movies/poster-8.png",
]

function make(
  id: number,
  title: string,
  posterIndex: number,
  opts: Partial<Movie> = {},
): Movie {
  return {
    id: `phim-${id}`,
    title,
    poster: posters[posterIndex % posters.length],
    year: 2020 + ((id * 3) % 6),
    rating: Number((6.8 + ((id * 7) % 30) / 10).toFixed(1)),
    duration: `${1 + (id % 2)}h ${5 + ((id * 13) % 55)}m`,
    genres: ["Hành động", "Chính kịch"],
    quality: (["4K", "HD", "HD", "4K"] as const)[id % 4],
    isNew: id % 5 === 0,
    ...opts,
  }
}

export const trending: Movie[] = [
  make(1, "Bí Ẩn Trong Mưa", 0, { genres: ["Hình sự", "Ly kỳ"], isNew: true }),
  make(2, "Vũ Trụ Vô Tận", 1, { genres: ["Viễn tưởng", "Phiêu lưu"] }),
  make(3, "Thanh Gươm Định Mệnh", 2, { genres: ["Giả tưởng", "Hành động"] }),
  make(4, "Hoàng Hôn Thành Phố", 3, { genres: ["Tình cảm", "Chính kịch"] }),
  make(5, "Truy Đuổi Nửa Đêm", 4, { genres: ["Hành động", "Ly kỳ"], isNew: true }),
  make(6, "Khu Rừng Câm Lặng", 5, { genres: ["Kinh dị", "Bí ẩn"] }),
  make(7, "Đảo Bay Kỳ Diệu", 6, { genres: ["Hoạt hình", "Gia đình"] }),
  make(8, "Chiến Trường Rực Lửa", 7, { genres: ["Chiến tranh", "Lịch sử"] }),
]

export const newReleases: Movie[] = [
  make(11, "Đảo Bay Kỳ Diệu", 6, { genres: ["Hoạt hình", "Gia đình"], isNew: true }),
  make(12, "Hoàng Hôn Thành Phố", 3, { genres: ["Tình cảm"], isNew: true }),
  make(13, "Vũ Trụ Vô Tận", 1, { genres: ["Viễn tưởng"], isNew: true }),
  make(14, "Khu Rừng Câm Lặng", 5, { genres: ["Kinh dị"], isNew: true }),
  make(15, "Bí Ẩn Trong Mưa", 0, { genres: ["Hình sự"], isNew: true }),
  make(16, "Chiến Trường Rực Lửa", 7, { genres: ["Chiến tranh"], isNew: true }),
  make(17, "Thanh Gươm Định Mệnh", 2, { genres: ["Giả tưởng"], isNew: true }),
  make(18, "Truy Đuổi Nửa Đêm", 4, { genres: ["Hành động"], isNew: true }),
]

export const topRated: Movie[] = [
  make(21, "Thanh Gươm Định Mệnh", 2, { genres: ["Giả tưởng"], rating: 9.2 }),
  make(22, "Chiến Trường Rực Lửa", 7, { genres: ["Chiến tranh"], rating: 9.0 }),
  make(23, "Bí Ẩn Trong Mưa", 0, { genres: ["Hình sự"], rating: 8.9 }),
  make(24, "Vũ Trụ Vô Tận", 1, { genres: ["Viễn tưởng"], rating: 8.8 }),
  make(25, "Khu Rừng Câm Lặng", 5, { genres: ["Kinh dị"], rating: 8.6 }),
  make(26, "Hoàng Hôn Thành Phố", 3, { genres: ["Tình cảm"], rating: 8.5 }),
  make(27, "Truy Đuổi Nửa Đêm", 4, { genres: ["Hành động"], rating: 8.4 }),
  make(28, "Đảo Bay Kỳ Diệu", 6, { genres: ["Hoạt hình"], rating: 8.3 }),
]

export const genreCategories = [
  "Tất cả",
  "Hành động",
  "Tình cảm",
  "Kinh dị",
  "Viễn tưởng",
  "Hoạt hình",
  "Chính kịch",
  "Hài",
]
