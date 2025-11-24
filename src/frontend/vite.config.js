import { defineConfig } from 'vite'
import path from 'path'

export default defineConfig({
  plugins: [],
  base: '/',
  root: path.resolve(__dirname, './renderer'),
  build: {
    outDir: path.resolve(__dirname, './dist'),
    emptyOutDir: true
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './renderer')
    }
  },
  server: {
    port: 5173,
    host: 'localhost',
    strictPort: true,
    open: false
  }
})

