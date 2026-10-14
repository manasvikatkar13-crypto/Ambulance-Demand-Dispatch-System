import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Configure Vite development server to run on port 5173
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
  },
});
