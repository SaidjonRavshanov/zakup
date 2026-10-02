import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // backend: uvicorn 127.0.0.1:8010 (README.md). localhost emas — Windows'da IPv6 kechikishi
    proxy: { '/api': process.env.ZAKUP_API_URL ?? 'http://127.0.0.1:8010' },
  },
  build: {
    target: 'es2022',
    cssCodeSplit: true,
  },
})
