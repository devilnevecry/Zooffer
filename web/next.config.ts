import type { NextConfig } from "next";

const apiInternal = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternal}/api/:path*`,
      },
      {
        // Media is served by FastAPI, not by Next. Without this rewrite every
        // photo URL breaks when the site and API run on different hosts.
        source: "/media/:path*",
        destination: `${apiInternal}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;
