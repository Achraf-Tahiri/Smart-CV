import { defineConfig, devices } from "@playwright/test";

// L'app est lancée à part (docker compose up) → pas de webServer auto ici.
// baseURL = front publié sur l'hôte (configurable avec E2E_BASE_URL).
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3001";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    // --no-sandbox : exécution en conteneur (image Playwright).
    launchOptions: { args: ["--no-sandbox"] },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
