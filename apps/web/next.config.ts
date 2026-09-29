import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Sortie autonome : image Docker minimale (server.js + assets nécessaires).
  output: "standalone",
  devIndicators: false,
  distDir: process.env.SMART_CV_PREVIEW === "1" ? ".preview-next" : ".next",
};

export default nextConfig;
