import screenshotDesktop from "screenshot-desktop";
import path from "node:path";
import fs from "node:fs";
import { app } from "electron";

export async function captureScreenshot(): Promise<string> {
  const dir = path.join(app.getPath("pictures"), "Jarvis Screenshots");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `jarvis-${Date.now()}.png`);
  await screenshotDesktop({ filename: file });
  return file;
}

export async function captureScreenshotBuffer(): Promise<Buffer> {
  return screenshotDesktop();
}

export async function captureScreenshotBase64(): Promise<{ mimeType: string; base64: string }> {
  const buffer = await screenshotDesktop();
  return { mimeType: "image/png", base64: buffer.toString("base64") };
}
