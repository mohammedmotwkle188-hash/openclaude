import { ipcMain } from "electron";
import { IPC } from "../../shared/types";
import { getOrCreateSalt, hasVaultBeenInitialized, rememberFact, recallFacts } from "../services/memory/db";
import { unlockVault, lockVault } from "../services/memory/encryption";
import { setSettings } from "../store";

export function registerMemoryIpc() {
  ipcMain.handle(IPC.memorySetPassphrase, (_evt, passphrase: string) => {
    const salt = getOrCreateSalt();
    unlockVault(passphrase, salt);
    setSettings({ hasPassphrase: true });
    return true;
  });

  ipcMain.handle(IPC.memoryUnlock, (_evt, passphrase: string) => {
    if (!hasVaultBeenInitialized()) return false;
    const salt = getOrCreateSalt();
    unlockVault(passphrase, salt);
    return true;
  });

  ipcMain.handle(IPC.memoryLock, () => {
    lockVault();
    return true;
  });

  ipcMain.handle(IPC.memoryRemember, (_evt, key: string, value: string) => {
    rememberFact(key, value);
    return true;
  });

  ipcMain.handle(IPC.memoryRecall, () => recallFacts());
}
