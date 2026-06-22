import { defineConfig } from 'vitest/config'

// Standalone config: unit tests target pure logic and run in node (no DOM/Vite plugins).
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'server/**/*.test.ts'],
  },
})
