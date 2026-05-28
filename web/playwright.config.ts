import { defineConfig, devices } from "@playwright/test";

const engineUrl = process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://127.0.0.1:8000";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const enginePython =
  process.env.PLAYWRIGHT_ENGINE_PYTHON ??
  (process.platform === "win32" ? ".\\.venv\\Scripts\\python.exe" : "python");
const externalServers = process.env.PLAYWRIGHT_EXTERNAL_SERVERS === "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["html", { outputFolder: "playwright-report", open: "never" }], ["list"]]
    : [["html", { outputFolder: "playwright-report", open: "never" }], ["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: externalServers
    ? undefined
    : [
    {
      command: `${enginePython} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "../engine",
      url: `${engineUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      gracefulShutdown: { signal: "SIGTERM", timeout: 500 },
      env: {
        ...(process.env.DATABASE_URL ? { DATABASE_URL: process.env.DATABASE_URL } : {}),
        ...(process.env.JWT_SECRET_KEY
          ? { JWT_SECRET_KEY: process.env.JWT_SECRET_KEY }
          : {}),
        ...(process.env.OLLAMA_URL ? { OLLAMA_URL: process.env.OLLAMA_URL } : {}),
        ...(process.env.OLLAMA_MODEL
          ? { OLLAMA_MODEL: process.env.OLLAMA_MODEL }
          : {}),
      },
    },
    {
      command: "npm run dev",
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 90_000,
      gracefulShutdown: { signal: "SIGTERM", timeout: 500 },
      env: {
        NEXT_PUBLIC_ENGINE_URL: engineUrl,
      },
    },
  ],
});
