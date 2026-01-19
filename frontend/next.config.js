/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Keep `ffmpeg-static` as an external dependency on the server
      config.externals.push('ffmpeg-static')
    }
    return config
  },
}

module.exports = nextConfig
