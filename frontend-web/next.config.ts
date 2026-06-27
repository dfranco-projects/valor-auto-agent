import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // self-contained server bundle for the docker image (.next/standalone/server.js)
  output: "standalone",
};

export default nextConfig;
