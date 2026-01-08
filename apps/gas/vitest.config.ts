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
      // Phase 2完了までテスト済みlib/ファイルのみ（handlers追加後に全体へ拡張）
      include: [
        "src/lib/common.ts",
        "src/lib/id_rules.ts",
        "src/lib/sheet_utils.ts",
      ],
      exclude: [
        "src/**/*.test.ts",
        "src/__mocks__/**",
        "src/tests/**",
      ],
      thresholds: {
        lines: 90,
        branches: 85,
        functions: 90,
        statements: 90,
      },
    },
  },
});
