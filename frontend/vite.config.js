import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The console calls /api on its own origin; Vite forwards it to Django. The officer laptop therefore only needs
// http://<server-ip>:5173. Set VITE_API_URL when the API lives elsewhere (Railway).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: {
      '/api': { target: process.env.AUDITRA_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  preview: {
    host: true,
    proxy: {
      '/api': { target: process.env.AUDITRA_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
