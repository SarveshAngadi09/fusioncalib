// Copyright (C) 2026 Sarvesh Angadi
// SPDX-License-Identifier: AGPL-3.0-or-later

const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

const PORT = 8000;
const HEALTH_URL = `http://127.0.0.1:${PORT}/health`;
const POLL_INTERVAL_MS = 500;
const MAX_WAIT_MS = 30000;

let mainWindow = null;
let serverProcess = null;

// ── Resolve path to Python server ────────────────────────────────
function getServerPath() {
  if (app.isPackaged) {
    // In production: server.exe bundled in extraResources
    return path.join(process.resourcesPath, "server", "server.exe");
  }
  // In development: run server.py directly with Python
  return null;
}

// ── Start Python FastAPI server ──────────────────────────────────
function startServer() {
  const serverExe = getServerPath();

  if (serverExe) {
    serverProcess = spawn(serverExe, [], { stdio: "pipe" });
  } else {
    // Dev mode — find server.py relative to electron/
    const serverScript = path.join(__dirname, "..", "calibration-api", "server.py");
    serverProcess = spawn("python", [serverScript], {
      stdio: "pipe",
      cwd: path.join(__dirname, "..", "calibration-api"),
    });
  }

  serverProcess.stdout.on("data", (d) => process.stdout.write(`[server] ${d}`));
  serverProcess.stderr.on("data", (d) => process.stderr.write(`[server] ${d}`));
  serverProcess.on("exit", (code) => {
    console.log(`[server] exited with code ${code}`);
  });
}

// ── Poll until the server is ready ──────────────────────────────
function waitForServer(timeout) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    function check() {
      http.get(HEALTH_URL, (res) => {
        if (res.statusCode === 200) return resolve();
        retry();
      }).on("error", retry);
    }

    function retry() {
      if (Date.now() - start > timeout) {
        return reject(new Error("Server did not start in time."));
      }
      setTimeout(check, POLL_INTERVAL_MS);
    }

    check();
  });
}

// ── Create the main window ───────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 720,
    minWidth: 600,
    minHeight: 500,
    title: "FusionCalib",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false,
    backgroundColor: "#0f1117",
  });

  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Open external links in the system browser, not in the app window.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("closed", () => { mainWindow = null; });
}

// ── Show a simple loading window while server starts ─────────────
function createLoadingWindow() {
  const loading = new BrowserWindow({
    width: 380,
    height: 200,
    frame: false,
    resizable: false,
    backgroundColor: "#0f1117",
    webPreferences: { nodeIntegration: false },
  });

  loading.loadURL(`data:text/html,
    <html><body style="margin:0;display:flex;flex-direction:column;
      align-items:center;justify-content:center;height:100vh;
      background:#0f1117;color:#e2e8f0;font-family:sans-serif">
      <div style="font-size:1.4rem;font-weight:700;margin-bottom:12px">FusionCalib</div>
      <div style="font-size:0.85rem;color:#64748b">Starting calibration server…</div>
    </body></html>
  `);

  return loading;
}

// ── App lifecycle ─────────────────────────────────────────────────
app.whenReady().then(async () => {
  const loading = createLoadingWindow();
  startServer();

  try {
    await waitForServer(MAX_WAIT_MS);
    loading.close();
    createWindow();
  } catch (err) {
    loading.close();
    console.error("Failed to start server:", err.message);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (serverProcess) serverProcess.kill();
  app.quit();
});

app.on("will-quit", () => {
  if (serverProcess) serverProcess.kill();
});
