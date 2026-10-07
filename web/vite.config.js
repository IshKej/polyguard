import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In development the React app runs on Vite and the Python API on uvicorn, so
// /api is proxied. In production both sit behind one origin (Vercel Services, or
// the API serving the built app locally).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Three.js on its own is about 520 kB minified. It is already split into its
    // own chunk and loads only after the page is readable (Bubble3D is lazy), so
    // the default 500 kB warning would only ever fire on that one file.
    chunkSizeWarningLimit: 600,
  },
  server: {
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})
