/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // YouTube thumbnails for storefront hero images.
    remotePatterns: [{ protocol: "https", hostname: "i.ytimg.com" }],
  },
};

export default nextConfig;
