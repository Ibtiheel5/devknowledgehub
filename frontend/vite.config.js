import { defineConfig } from "vite";

export default defineConfig({
  // Les fichiers .jsx n'importent pas React : on active le runtime JSX automatique.
  esbuild: {
    jsx: "automatic"
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000"
    }
  }
});
