import fs from "node:fs";
import path from "node:path";
import { app } from "electron";
import type { ApiKeySet, AppSettings, AiProviderId } from "../shared/types";

interface StoreShape {
  settings: AppSettings;
  apiKeys: ApiKeySet;
}

const defaults: StoreShape = {
  settings: {
    theme: "dark",
    animationsEnabled: true,
    wakeWordEnabled: true,
    voiceEnabled: true,
    voiceName: null,
    speechRate: 1.05,
    providerOrder: ["anthropic", "openai", "gemini", "ollama"],
    ollamaBaseUrl: "http://127.0.0.1:11434",
    weatherLocation: "London,UK",
    hasPassphrase: false,
  },
  apiKeys: {},
};

// Plain JSON on disk in the OS-protected app-data directory. This is fine for local
// settings, but API keys deserve better than a readable file — wire this up to the
// platform credential manager (`keytar`, Keychain/Credential Manager/libsecret) before
// shipping to real users. electron-store's own `encryptionKey` option would not have
// improved on this: the key ships in the app binary, so it is obfuscation, not security.
let cache: StoreShape | null = null;

function filePath() {
  return path.join(app.getPath("userData"), "jarvis-config.json");
}

function load(): StoreShape {
  if (cache) return cache;
  try {
    const raw = fs.readFileSync(filePath(), "utf8");
    const parsed = JSON.parse(raw);
    cache = {
      settings: { ...defaults.settings, ...parsed.settings },
      apiKeys: { ...defaults.apiKeys, ...parsed.apiKeys },
    };
  } catch {
    cache = { settings: { ...defaults.settings }, apiKeys: { ...defaults.apiKeys } };
  }
  return cache;
}

function persist() {
  if (!cache) return;
  fs.mkdirSync(path.dirname(filePath()), { recursive: true });
  fs.writeFileSync(filePath(), JSON.stringify(cache, null, 2), { mode: 0o600 });
}

export function getSettings(): AppSettings {
  return load().settings;
}

export function setSettings(partial: Partial<AppSettings>) {
  const store = load();
  store.settings = { ...store.settings, ...partial };
  persist();
}

export function getApiKey(provider: keyof ApiKeySet): string | undefined {
  return load().apiKeys[provider];
}

export function setApiKeys(partial: Partial<ApiKeySet>) {
  const store = load();
  store.apiKeys = { ...store.apiKeys, ...partial };
  persist();
}

export function getMaskedApiKeys(): Record<keyof ApiKeySet, boolean> {
  const keys = load().apiKeys;
  return {
    anthropic: !!keys.anthropic,
    openai: !!keys.openai,
    gemini: !!keys.gemini,
    openweather: !!keys.openweather,
    newsapi: !!keys.newsapi,
  };
}

export function providerConfigured(id: AiProviderId): boolean {
  if (id === "ollama") return true;
  return !!getApiKey(id);
}
