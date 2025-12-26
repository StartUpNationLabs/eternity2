import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'


// https://vitejs.dev/config/
export default defineConfig({
  // Support deployment under a path prefix (e.g., /eternity2)
  // Set via BASE_PATH environment variable, defaults to root
  base: process.env.BASE_PATH || '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    target: 'es2022',
    commonjsOptions: { transformMixedEsModules: true } // Change
  }
})
