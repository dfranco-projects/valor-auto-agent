import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // self-contained server bundle for the docker image (.next/standalone/server.js)
  output: "standalone",
  // hide the floating dev indicator in the bottom-left corner
  devIndicators: false,
};

export default nextConfig;
