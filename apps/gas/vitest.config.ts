import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["src/**/*.test.ts"],
    setupFiles: ["./src/__mocks__/gas-stubs.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      // lib/ + handlers/ をカバレッジ対象にする
      include: [
        "src/lib/**/*.ts",
        "src/handlers/**/*.ts",
      ],
      exclude: [
        "src/**/*.test.ts",
        "src/__mocks__/**",
        "src/tests/**",
        "src/handlers/__tests__/**",
      ],
      thresholds: {
        // 現状: lines 85.7%, branches 68.86%, functions 93.75%
        lines: 80,
        branches: 60,
        functions: 90,
        statements: 80,
      },
    },
  },
});
