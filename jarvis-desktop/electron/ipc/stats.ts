import { ipcMain, BrowserWindow } from "electron";
import { IPC } from "../../shared/types";
import { collectSystemStats, checkInternetOnline } from "../services/system/stats";

export function registerStatsIpc(win: BrowserWindow) {
  let timer: NodeJS.Timeout | null = null;
  let netTimer: NodeJS.Timeout | null = null;

  ipcMain.handle(IPC.statsSubscribe, () => {
    if (timer) clearInterval(timer);
    const tick = async () => {
      if (win.isDestroyed()) return;
      const stats = await collectSystemStats().catch(() => null);
      if (stats) win.webContents.send(IPC.statsUpdate, stats);
    };
    tick();
    timer = setInterval(tick, 2000);

    if (netTimer) clearInterval(netTimer);
    const netTick = async () => {
      if (win.isDestroyed()) return;
      const online = await checkInternetOnline();
      win.webContents.send(IPC.internetStatus, online);
    };
    netTick();
    netTimer = setInterval(netTick, 10000);
    return true;
  });

  win.on("closed", () => {
    if (timer) clearInterval(timer);
    if (netTimer) clearInterval(netTimer);
  });
}
