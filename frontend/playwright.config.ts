import { fileURLToPath } from "url";
import path from "path";
import { defineConfig, devices } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./e2e",
  snapshotDir: "./e2e/snapshots",
  fullyParallel: true,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium-mobile",
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: [
    {
      command: "pnpm dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env["CI"],
    },
    {
      command: "uv run uvicorn ficsolver.main:app --port 8000",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env["CI"],
      cwd: "../backend",
      env: {
        ...process.env,
        GAME_DATA_PATH:
          process.env["GAME_DATA_PATH"] ??
          path.resolve(__dirname, "../backend/tests/fixtures/e2e-game-data.json"),
      },
    },
  ],
  // Generate baselines if they don't exist yet; fail on diff thereafter
  updateSnapshots: "missing",
});
