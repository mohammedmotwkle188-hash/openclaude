import { ipcMain, BrowserWindow } from "electron";
import { IPC } from "../../shared/types";

export function registerWindowIpc(win: BrowserWindow) {
  ipcMain.handle(IPC.windowMinimize, () => win.minimize());
  ipcMain.handle(IPC.windowClose, () => win.close());
}
