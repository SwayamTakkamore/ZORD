/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // Use pages directory (default in Next.js 14)
  env: {
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
    NEXT_PUBLIC_EXPLORER_BASE_URL: process.env.NEXT_PUBLIC_EXPLORER_BASE_URL || 'https://testnet-zkevm.polygonscan.com'
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/:path*`
      }
    ]
  },
  images: {
    domains: ['localhost']
  }
}

module.exports = nextConfig
