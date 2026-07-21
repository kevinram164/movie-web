/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || 'http://movie-api:8080'
    // MinIO nội bộ; browser chỉ gọi /media cùng origin (MinIO không public)
    const mediaTarget = process.env.MEDIA_PROXY_TARGET || 'http://minio.minio.svc.cluster.local:9000'
    return [
      {
        source: '/api/:path*',
        destination: `${target}/api/:path*`,
      },
      {
        source: '/media/:path*',
        destination: `${mediaTarget}/:path*`,
      },
    ]
  },
}

export default nextConfig
