import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    allowedHosts: ['sb-29q8tisf0yuf.vercel.run', '.vercel.run'],
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
