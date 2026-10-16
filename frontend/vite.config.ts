import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env };
  const proxy =
    env.VITE_AUTH_SAME_ORIGIN_PROXY === 'true'
      ? { '/api/v1/auth/': { target: env.VITE_API_BASE_URL, changeOrigin: false } }
      : undefined;
  return {
    plugins: [react()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, strictPort: true, proxy },
    build: { sourcemap: false },
  };
});
