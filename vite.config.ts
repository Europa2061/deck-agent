import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  resolve: { alias: { '@decky/ui': fileURLToPath(new URL('./src/dev/decky-ui.tsx', import.meta.url)) } },
  server: { proxy: { '/api': 'http://127.0.0.1:4314' } },
});
