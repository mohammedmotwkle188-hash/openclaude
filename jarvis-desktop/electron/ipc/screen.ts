import { ipcMain, BrowserWindow } from "electron";
import { randomUUID } from "node:crypto";
import { IPC } from "../../shared/types";
import { captureScreenshot, captureScreenshotBuffer, captureScreenshotBase64 } from "../services/screen/capture";
import { extractTextFromImage } from "../services/screen/ocr";

export function registerScreenIpc(win: BrowserWindow) {
  let monitorTimer: NodeJS.Timeout | null = null;

  ipcMain.handle(IPC.screenshotCapture, async () => captureScreenshot());
  ipcMain.handle(IPC.screenCaptureBase64, async () => captureScreenshotBase64());

  ipcMain.handle(IPC.screenOcr, async () => {
    const buffer = await captureScreenshotBuffer();
    return extractTextFromImage(buffer);
  });

  ipcMain.handle(IPC.screenMonitorToggle, (_evt, enabled: boolean) => {
    if (monitorTimer) {
      clearInterval(monitorTimer);
      monitorTimer = null;
    }
    if (enabled) {
      monitorTimer = setInterval(async () => {
        if (win.isDestroyed()) return;
        try {
          const buffer = await captureScreenshotBuffer();
          const text = await extractTextFromImage(buffer);
          win.webContents.send(IPC.notify, {
            id: randomUUID(),
            title: "Screen scan",
            body: text.slice(0, 240) || "(no legible text detected)",
            level: "info",
            timestamp: Date.now(),
          });
        } catch {
          // Screen monitoring is best-effort; a failed capture shouldn't crash the loop.
        }
      }, 15000);
    }
    return enabled;
  });

  win.on("closed", () => {
    if (monitorTimer) clearInterval(monitorTimer);
  });
}
