import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    proxy: {
      "/dashboard": {
        target: "http://localhost:5174",
        changeOrigin: true,
      },
    },
  },
});
