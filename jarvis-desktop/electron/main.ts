import { app, BrowserWindow, shell } from "electron";
import path from "node:path";
import { initDb } from "./services/memory/db";
import { registerStatsIpc } from "./ipc/stats";
import { registerChatIpc } from "./ipc/chat";
import { registerMemoryIpc } from "./ipc/memory";
import { registerCommandIpc } from "./ipc/commands";
import { registerSettingsIpc } from "./ipc/settings";
import { registerScreenIpc } from "./ipc/screen";
import { registerDataIpc } from "./ipc/data";
import { registerWindowIpc } from "./ipc/window";
import { registerVoiceIpc } from "./ipc/voice";

const isDev = !app.isPackaged;

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#020408",
    frame: false,
    titleBarStyle: "hidden",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // Every outbound navigation/new-window request is routed to the OS browser instead
  // of being loaded inside the app — the HUD has no business rendering third-party pages.
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith("file://") && !url.startsWith("http://localhost")) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  if (isDev) {
    win.loadURL("http://localhost:5173");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "../../dist/index.html"));
  }

  registerStatsIpc(win);
  registerChatIpc(win);
  registerMemoryIpc();
  registerCommandIpc();
  registerSettingsIpc();
  registerScreenIpc(win);
  registerDataIpc();
  registerWindowIpc(win);
  registerVoiceIpc();

  return win;
}

app.whenReady().then(() => {
  initDb();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
