// Shared type contracts between the Electron main process and the renderer HUD.
// Imported by both sides — keep this file free of runtime-only Node/DOM APIs.

export interface SystemStatsSnapshot {
  timestamp: number;
  cpu: { loadPercent: number; cores: number; speedGhz: number; model: string };
  ram: { usedGb: number; totalGb: number; usedPercent: number };
  gpu: { model: string; loadPercent: number | null; vramUsedMb: number | null; vramTotalMb: number | null };
  battery: { hasBattery: boolean; percent: number; isCharging: boolean; timeRemainingMin: number | null };
  storage: { usedGb: number; totalGb: number; usedPercent: number };
  network: { interface: string; downKbps: number; upKbps: number; online: boolean };
  temperature: { cpuC: number | null };
  processes: { total: number; running: number; topByCpu: Array<{ name: string; cpuPercent: number }> };
}

export type AiProviderId = "anthropic" | "openai" | "gemini" | "openrouter" | "ollama";

export interface ProviderStatus {
  id: AiProviderId;
  configured: boolean;
  reachable: boolean | null;
}

export interface ImageAttachment {
  mimeType: string;
  base64: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  timestamp: number;
  provider?: AiProviderId;
  pending?: boolean;
  /** Transient — attached for a single vision-capable request, never persisted to disk. */
  image?: ImageAttachment;
}

export interface ChatStreamChunk {
  requestId: string;
  delta?: string;
  done?: boolean;
  error?: string;
  provider?: AiProviderId;
}

export interface AssistantThought {
  id: string;
  text: string;
  timestamp: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  level: "info" | "warning" | "critical";
  timestamp: number;
}

export interface ReminderItem {
  id: string;
  text: string;
  dueAt: number;
  done: boolean;
}

export interface CalendarEventItem {
  id: string;
  title: string;
  startAt: number;
  endAt: number;
}

export interface WeatherSnapshot {
  location: string;
  tempC: number;
  condition: string;
  humidityPercent: number;
  updatedAt: number;
}

export interface NewsHeadline {
  id: string;
  title: string;
  source: string;
  url: string;
  publishedAt: number;
}

export type CommandRiskLevel = "safe" | "confirm";

export interface ParsedCommand {
  id: string;
  raw: string;
  action: string;
  args: Record<string, string>;
  risk: CommandRiskLevel;
  label: string;
}

export interface CommandResult {
  id: string;
  ok: boolean;
  message: string;
}

export interface AppSettings {
  theme: "dark" | "darker";
  animationsEnabled: boolean;
  wakeWordEnabled: boolean;
  voiceEnabled: boolean;
  voiceName: string | null;
  elevenLabsVoiceId: string | null;
  ttsProvider: "auto" | "elevenlabs" | "edge" | "offline";
  speechRate: number;
  providerOrder: AiProviderId[];
  ollamaBaseUrl: string;
  weatherLocation: string;
  hasPassphrase: boolean;
}

export interface ApiKeySet {
  anthropic?: string;
  openai?: string;
  gemini?: string;
  openrouter?: string;
  elevenlabs?: string;
  openweather?: string;
  newsapi?: string;
  wolfram?: string;
}

export const DANGEROUS_ACTIONS = [
  "shutdown_pc",
  "restart_pc",
  "delete_file",
  "delete_folder",
] as const;

export type DangerousAction = (typeof DANGEROUS_ACTIONS)[number];

export const IPC = {
  statsSubscribe: "stats:subscribe",
  statsUpdate: "stats:update",
  internetStatus: "net:status",

  chatSend: "chat:send",
  chatStream: "chat:stream",
  chatInterrupt: "chat:interrupt",
  chatHistoryGet: "chat:history:get",
  chatHistoryClear: "chat:history:clear",
  providerStatus: "provider:status",

  memoryRemember: "memory:remember",
  memoryRecall: "memory:recall",
  memorySetPassphrase: "memory:setPassphrase",
  memoryUnlock: "memory:unlock",
  memoryLock: "memory:lock",

  commandParse: "command:parse",
  commandExecute: "command:execute",

  settingsGet: "settings:get",
  settingsSet: "settings:set",
  apiKeysSet: "apiKeys:set",
  apiKeysGetMasked: "apiKeys:getMasked",

  screenshotCapture: "screen:capture",
  screenCaptureBase64: "screen:captureBase64",
  screenOcr: "screen:ocr",
  screenMonitorToggle: "screen:monitorToggle",

  remindersList: "reminders:list",
  remindersAdd: "reminders:add",
  remindersToggle: "reminders:toggle",
  calendarList: "calendar:list",

  weatherGet: "weather:get",
  newsGet: "news:get",
  stockGet: "stock:get",
  cryptoGet: "crypto:get",

  notify: "notify:push",

  windowMinimize: "win:minimize",
  windowClose: "win:close",
} as const;
