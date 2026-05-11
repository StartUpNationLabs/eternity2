import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@wasm": path.resolve(__dirname, "../wasm/pkg"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/grpc": {
        target: "http://127.0.0.1:50051",
        changeOrigin: true,
        ws: false,
        rewrite: (p) => p.replace(/^\/grpc/, ""),
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
