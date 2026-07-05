import { ipcMain } from "electron";
import { IPC } from "../../shared/types";
import type { AppSettings, ApiKeySet } from "../../shared/types";
import { getSettings, setSettings, setApiKeys, getMaskedApiKeys } from "../store";

export function registerSettingsIpc() {
  ipcMain.handle(IPC.settingsGet, () => getSettings());
  ipcMain.handle(IPC.settingsSet, (_evt, partial: Partial<AppSettings>) => {
    setSettings(partial);
    return getSettings();
  });
  ipcMain.handle(IPC.apiKeysSet, (_evt, partial: Partial<ApiKeySet>) => {
    setApiKeys(partial);
    return true;
  });
  ipcMain.handle(IPC.apiKeysGetMasked, () => getMaskedApiKeys());
}
