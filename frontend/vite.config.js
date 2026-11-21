import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // In production (Vercel) VITE_API_BASE is injected from env variables.
  // In local dev it falls back to http://localhost:8000 (see src files).
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8080',
      '/cases': 'http://127.0.0.1:8080',
      '/query': 'http://127.0.0.1:8080',
      '/moot-court': 'http://127.0.0.1:8080',
      '/draft': 'http://127.0.0.1:8080',
      '/bns': 'http://127.0.0.1:8080',
      '/health': 'http://127.0.0.1:8080',
      '/system': 'http://127.0.0.1:8080',
      '/notice': 'http://127.0.0.1:8080',
      '/similar-cases': 'http://127.0.0.1:8080',
      '/citizen-advice': 'http://127.0.0.1:8080',
    },
  },
  build: {
    sourcemap: false,       // smaller bundle for production
    chunkSizeWarningLimit: 600,
  },
})
