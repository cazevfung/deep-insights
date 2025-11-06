import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
// @ts-ignore - JavaScript module, no TypeScript definitions
import serverConfig from './scripts/read-config.js'

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: serverConfig.frontendHost, // Read from config.yaml
    port: serverConfig.frontendPort,
    proxy: {
      '/api': {
        target: serverConfig.proxyTarget,
        changeOrigin: true,
        timeout: serverConfig.proxyTimeout,
        proxyTimeout: serverConfig.proxyTimeout,
      },
      '/health': {
        target: serverConfig.proxyTarget,
        changeOrigin: true,
        timeout: serverConfig.proxyTimeout,
        proxyTimeout: serverConfig.proxyTimeout,
      },
      '/ws': {
        target: `http://localhost:${serverConfig.backendPort}`,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})


