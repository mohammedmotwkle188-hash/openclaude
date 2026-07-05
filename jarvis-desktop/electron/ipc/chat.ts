import { randomUUID } from "node:crypto";
import { ipcMain, BrowserWindow } from "electron";
import { IPC } from "../../shared/types";
import type { ChatMessage } from "../../shared/types";
import { streamWithFallback, getProviderStatuses } from "../services/ai/router";
import { loadHistory, saveMessage, clearHistory, recallFacts } from "../services/memory/db";

const activeStreams = new Map<string, AbortController>();

export function registerChatIpc(win: BrowserWindow) {
  ipcMain.handle(IPC.chatHistoryGet, () => loadHistory());
  ipcMain.handle(IPC.chatHistoryClear, () => clearHistory());
  ipcMain.handle(IPC.providerStatus, () => getProviderStatuses());

  ipcMain.handle(IPC.chatSend, async (_evt, turns: ChatMessage[]) => {
    const requestId = randomUUID();
    const controller = new AbortController();
    activeStreams.set(requestId, controller);

    const userTurn = turns[turns.length - 1];
    if (userTurn) saveMessage(userTurn);

    (async () => {
      let full = "";
      try {
        const facts = recallFacts();
        const factLines = Object.entries(facts)
          .filter(([, v]) => v !== "[locked]")
          .map(([k, v]) => `- ${k}: ${v}`)
          .join("\n");
        const provider = await streamWithFallback(
          turns.map((t) => ({ role: t.role, text: t.text, image: t.image })),
          (delta, prov) => {
            full += delta;
            win.webContents.send(IPC.chatStream, { requestId, delta, provider: prov });
          },
          controller.signal,
          factLines || undefined,
        );
        win.webContents.send(IPC.chatStream, { requestId, done: true, provider });
        if (full.trim()) {
          saveMessage({ id: randomUUID(), role: "assistant", text: full, timestamp: Date.now(), provider });
        }
      } catch (err: any) {
        win.webContents.send(IPC.chatStream, { requestId, error: err?.message ?? String(err), done: true });
      } finally {
        activeStreams.delete(requestId);
      }
    })();

    return requestId;
  });

  ipcMain.handle(IPC.chatInterrupt, (_evt, requestId: string) => {
    activeStreams.get(requestId)?.abort();
    activeStreams.delete(requestId);
    return true;
  });
}
