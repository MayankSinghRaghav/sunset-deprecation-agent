import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle for a lean production container.
  output: "standalone",
};

export default nextConfig;
