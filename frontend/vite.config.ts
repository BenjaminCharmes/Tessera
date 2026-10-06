import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Isole monaco-editor (et @monaco-editor/react) dans leur propre chunk
        // — chargés uniquement quand l'éditeur s'ouvre, pas au démarrage de
        // l'application (ticket-355, ADR-012).
        manualChunks: (id: string) => {
          if (id.includes("monaco-editor") || id.includes("@monaco-editor/react")) {
            return "monaco-editor";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    testTimeout: 15000,
    hookTimeout: 15000,
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["**/node_modules/**", "**/e2e/**"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**", "src/hooks/**", "src/components/**"],
      exclude: ["src/**/*.test.*", "src/test/**"],
      thresholds: { lines: 78, branches: 65, functions: 70 },
      reporter: ["text", "html", "lcov"],
    },
  },
});
