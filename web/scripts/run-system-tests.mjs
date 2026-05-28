import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const isWindows = process.platform === "win32";
const webDir = fileURLToPath(new URL("..", import.meta.url));
const engineDir = fileURLToPath(new URL("../../engine", import.meta.url));
const engineUrl = process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://127.0.0.1:8000";
const baseUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const enginePython =
  process.env.PLAYWRIGHT_ENGINE_PYTHON ??
  (isWindows ? ".\\.venv\\Scripts\\python.exe" : "python");

const extraArgs = process.argv.slice(2);

function spawnProcess(command, args, options = {}) {
  return spawn(command, args, {
    stdio: "inherit",
    shell: isWindows,
    detached: !isWindows,
    ...options,
  });
}

async function waitFor(url, label) {
  const deadline = Date.now() + 90_000;
  let lastError = "";

  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
      lastError = `${response.status} ${response.statusText}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
    await delay(1000);
  }

  throw new Error(`${label} did not become ready at ${url}: ${lastError}`);
}

async function stopProcess(child) {
  if (!child || child.killed) {
    return;
  }

  if (isWindows) {
    await Promise.race([
      new Promise((resolve) => {
      const killer = spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
        shell: false,
      });
      killer.on("exit", resolve);
      killer.on("error", resolve);
      }),
      delay(3000),
    ]);
    return;
  }

  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    child.kill("SIGTERM");
  }
}

const children = [];

try {
  const engine = spawnProcess(
    enginePython,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: engineDir,
      env: { ...process.env },
    }
  );
  children.push(engine);

  await waitFor(`${engineUrl}/health`, "Engine");

  const npmCommand = isWindows ? "npm.cmd" : "npm";
  const web = spawnProcess(npmCommand, ["run", "dev"], {
    cwd: webDir,
    env: {
      ...process.env,
      NEXT_PUBLIC_ENGINE_URL: engineUrl,
    },
  });
  children.push(web);

  await waitFor(baseUrl, "Next.js");

  const npxCommand = isWindows ? "npx.cmd" : "npx";
  const playwright = spawnProcess(
    npxCommand,
    ["playwright", "test", ...extraArgs],
    {
      cwd: webDir,
      env: {
        ...process.env,
        PLAYWRIGHT_EXTERNAL_SERVERS: "1",
        NEXT_PUBLIC_ENGINE_URL: engineUrl,
        PLAYWRIGHT_BASE_URL: baseUrl,
      },
    }
  );

  const exitCode = await new Promise((resolve) => {
    playwright.on("exit", (code) => resolve(code ?? 1));
    playwright.on("error", () => resolve(1));
  });

  process.exitCode = Number(exitCode);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
} finally {
  await Promise.all(children.reverse().map(stopProcess));
}

process.exit(process.exitCode ?? 0);
