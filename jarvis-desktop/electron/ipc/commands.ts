import { ipcMain } from "electron";
import { IPC } from "../../shared/types";
import { parseCommand } from "../services/system/parser";
import { executeCommand } from "../services/system/dispatcher";

export function registerCommandIpc() {
  ipcMain.handle(IPC.commandParse, (_evt, raw: string) => parseCommand(raw));
  ipcMain.handle(IPC.commandExecute, (_evt, cmd) => executeCommand(cmd));
}
