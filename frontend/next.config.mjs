/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      // YouTube thumbnails for storefront hero images.
      { protocol: "https", hostname: "i.ytimg.com" },
      // TikTok covers, copied into Supabase Storage because TikTok's own
      // cover links expire after two days.
      {
        protocol: "https",
        hostname: "*.supabase.co",
        pathname: "/storage/v1/object/public/video-covers/**",
      },
    ],
  },
};

export default nextConfig;
