import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const isProduction = mode === 'production';
  
  return {
    plugins: [react()],
    build: {
      outDir: 'dist',
      minify: isProduction ? 'terser' : false,
      terserOptions: isProduction ? {
        compress: {
          drop_console: true,      // Remove all console.* statements
          drop_debugger: true,     // Remove debugger statements
          pure_funcs: [
            'console.log',
            'console.error',
            'console.warn',
            'console.debug',
            'console.info',
            'console.trace',
            'console.dir',
            'console.table',
            'console.time',
            'console.timeEnd',
            'console.timeLog',
            'console.assert',
            'console.clear',
            'console.count',
            'console.countReset',
            'console.group',
            'console.groupEnd',
            'console.groupCollapsed'
          ],
          passes: 2               // Run compression twice for better results
        },
        mangle: {
          safari10: true         // Support Safari 10
        },
        format: {
          comments: false        // Remove all comments
        }
      } : {},
      rollupOptions: {
        input: {
          main: 'index.html',
          embed: 'src/embed.ts'
        },
        output: {
          entryFileNames: (chunkInfo) => {
            if (chunkInfo.name === 'embed') {
              return 'embed.js'
            }
            return 'assets/[name]-[hash].js'
          },
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]'
        }
      }
    },
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode)
    },
    esbuild: {
      // Also remove console in development builds if needed
      drop: isProduction ? ['console', 'debugger'] : []
    }
  }
})