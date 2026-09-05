import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Relative asset paths so the built site can be dropped on any static host.
  base: './',
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
  },
});
