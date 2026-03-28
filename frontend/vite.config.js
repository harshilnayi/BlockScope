import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
  ],


  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
    include: ['src/_tests_/**/*.{test,spec}.{js,jsx}'],
  },

  build: {
    // Target modern browsers — smaller output, no legacy transforms
    target: 'es2020',

    // Warn when any chunk exceeds 400 KB (before gzip)
    chunkSizeWarningLimit: 400,

    // Enable Rollup tree-shaking
    rollupOptions: {
      output: {
        /**
         * Manual chunk splitting strategy:
         *   - react-vendor   : React + ReactDOM (rarely changes → long cache)
         *   - ui-vendor      : lucide-react, react-tooltip, react-joyride
         *   - app            : application code
         *
         * Each chunk gets its own content-hash file name so CDN/browser
         * caches are invalidated precisely when that chunk changes.
         */
        manualChunks(id) {
          if (id.includes('node_modules')) {
            const isPackage = (pkgName) => (
              id.includes(`/node_modules/${pkgName}/`) ||
              id.includes(`\\node_modules\\${pkgName}\\`)
            )

            if (isPackage('react') || isPackage('react-dom') || isPackage('scheduler')) {
              return 'react-vendor'
            }
            if (
              isPackage('lucide-react') ||
              isPackage('react-tooltip') ||
              isPackage('react-joyride')
            ) {
              return 'ui-vendor'
            }
            return 'vendor'
          }
        },

        // Consistent chunk naming with content hash for cache-busting
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },

    // Generate source maps for production error tracking (external, not inlined)
    sourcemap: false,

    // Minify with esbuild (default) — fastest option
    minify: 'esbuild',

    // CSS code-splitting: each async chunk only loads the CSS it needs
    cssCodeSplit: true,
  },

  // Dev server proxy to avoid CORS issues during development
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },

  // Optimize deps ahead-of-time for faster cold starts
  optimizeDeps: {
    include: ['react', 'react-dom', 'lucide-react'],
  },
})
