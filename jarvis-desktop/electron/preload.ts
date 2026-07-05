import { contextBridge, ipcRenderer } from "electron";
import { IPC } from "../shared/types";
import type {
  AppSettings,
  ApiKeySet,
  CalendarEventItem,
  ChatMessage,
  ChatStreamChunk,
  NewsHeadline,
  NotificationItem,
  ParsedCommand,
  ReminderItem,
  SystemStatsSnapshot,
  WeatherSnapshot,
} from "../shared/types";

const api = {
  stats: {
    subscribe: () => ipcRenderer.invoke(IPC.statsSubscribe),
    onUpdate: (cb: (s: SystemStatsSnapshot) => void) => {
      const listener = (_: unknown, data: SystemStatsSnapshot) => cb(data);
      ipcRenderer.on(IPC.statsUpdate, listener);
      return () => {
        ipcRenderer.removeListener(IPC.statsUpdate, listener);
      };
    },
    onInternetStatus: (cb: (online: boolean) => void) => {
      const listener = (_: unknown, online: boolean) => cb(online);
      ipcRenderer.on(IPC.internetStatus, listener);
      return () => {
        ipcRenderer.removeListener(IPC.internetStatus, listener);
      };
    },
  },
  chat: {
    send: (turns: ChatMessage[]) => ipcRenderer.invoke(IPC.chatSend, turns) as Promise<string>,
    interrupt: (requestId: string) => ipcRenderer.invoke(IPC.chatInterrupt, requestId),
    getHistory: () => ipcRenderer.invoke(IPC.chatHistoryGet) as Promise<ChatMessage[]>,
    clearHistory: () => ipcRenderer.invoke(IPC.chatHistoryClear),
    providerStatus: () => ipcRenderer.invoke(IPC.providerStatus),
    onStream: (cb: (chunk: ChatStreamChunk) => void) => {
      const listener = (_: unknown, chunk: ChatStreamChunk) => cb(chunk);
      ipcRenderer.on(IPC.chatStream, listener);
      return () => {
        ipcRenderer.removeListener(IPC.chatStream, listener);
      };
    },
  },
  memory: {
    setPassphrase: (pass: string) => ipcRenderer.invoke(IPC.memorySetPassphrase, pass) as Promise<boolean>,
    unlock: (pass: string) => ipcRenderer.invoke(IPC.memoryUnlock, pass) as Promise<boolean>,
    lock: () => ipcRenderer.invoke(IPC.memoryLock),
    remember: (key: string, value: string) => ipcRenderer.invoke(IPC.memoryRemember, key, value),
    recall: () => ipcRenderer.invoke(IPC.memoryRecall) as Promise<Record<string, string>>,
  },
  commands: {
    parse: (raw: string) => ipcRenderer.invoke(IPC.commandParse, raw) as Promise<ParsedCommand | null>,
    execute: (cmd: ParsedCommand) => ipcRenderer.invoke(IPC.commandExecute, cmd),
  },
  settings: {
    get: () => ipcRenderer.invoke(IPC.settingsGet) as Promise<AppSettings>,
    set: (partial: Partial<AppSettings>) => ipcRenderer.invoke(IPC.settingsSet, partial) as Promise<AppSettings>,
    setApiKeys: (partial: Partial<ApiKeySet>) => ipcRenderer.invoke(IPC.apiKeysSet, partial),
    getMaskedApiKeys: () => ipcRenderer.invoke(IPC.apiKeysGetMasked),
  },
  screen: {
    capture: () => ipcRenderer.invoke(IPC.screenshotCapture) as Promise<string>,
    captureBase64: () => ipcRenderer.invoke(IPC.screenCaptureBase64) as Promise<{ mimeType: string; base64: string }>,
    ocr: () => ipcRenderer.invoke(IPC.screenOcr) as Promise<string>,
    toggleMonitor: (enabled: boolean) => ipcRenderer.invoke(IPC.screenMonitorToggle, enabled),
  },
  data: {
    weather: (location?: string) => ipcRenderer.invoke(IPC.weatherGet, location) as Promise<WeatherSnapshot>,
    news: () => ipcRenderer.invoke(IPC.newsGet) as Promise<NewsHeadline[]>,
    stock: (symbol: string) => ipcRenderer.invoke(IPC.stockGet, symbol) as Promise<string>,
    crypto: (symbol: string) => ipcRenderer.invoke(IPC.cryptoGet, symbol) as Promise<string>,
    remindersList: () => ipcRenderer.invoke(IPC.remindersList) as Promise<ReminderItem[]>,
    remindersAdd: (text: string, dueAt: number) => ipcRenderer.invoke(IPC.remindersAdd, text, dueAt) as Promise<ReminderItem>,
    remindersToggle: (id: string) => ipcRenderer.invoke(IPC.remindersToggle, id),
    calendarList: () => ipcRenderer.invoke(IPC.calendarList) as Promise<CalendarEventItem[]>,
  },
  notifications: {
    onNotify: (cb: (n: NotificationItem) => void) => {
      const listener = (_: unknown, n: NotificationItem) => cb(n);
      ipcRenderer.on(IPC.notify, listener);
      return () => {
        ipcRenderer.removeListener(IPC.notify, listener);
      };
    },
  },
  window: {
    minimize: () => ipcRenderer.invoke(IPC.windowMinimize),
    close: () => ipcRenderer.invoke(IPC.windowClose),
  },
};

contextBridge.exposeInMainWorld("jarvis", api);

export type JarvisApi = typeof api;
