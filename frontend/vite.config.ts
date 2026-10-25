/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // همان‌مبدا برای توسعه — پالایش درون dev به backend محلی
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    includeSource: ['src/**/*.{ts,tsx}'],
    // Force the React development build in tests: NODE_ENV=production leaks in
    // from some shells and the prod build has no React.act, which breaks RTL.
    env: { NODE_ENV: 'test' },
  },
})
