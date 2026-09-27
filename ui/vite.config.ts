   import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Proxy /api/*     api-gateway port-forward (kubectl port-forward svc/api-gateway 58663:80 -n incident-agent-system)
      // In production (containerized), NGINX in the UI image handles this routing internally.
      '/api': {
        target: 'http://localhost:58663',
        changeOrigin: true,
      }
    }
  }
})
