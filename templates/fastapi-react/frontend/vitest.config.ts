import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Config vitest séparée de vite.config.ts : tsconfig.node.json n'inclut que
// vite.config.ts, ce qui évite un conflit de types entre vitest et vite.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    globals: true,
    clearMocks: true,
  },
});
