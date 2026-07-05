// Replaces Electron's preload.ts + IPC for the pywebview build: pywebview exposes Python
// methods at window.pywebview.api.<flat_name>(...) (all async, all flat — no nesting), and
// Python pushes events back by evaluating `window.__jarvisPush(channel, payload)` in the
// page. This module rebuilds the same window.jarvis.* shape the UI components already use,
// just backed by Python instead of an Electron main process. Importing this file (for its
// side effect) must happen before anything else touches window.jarvis.

type Listener = (payload: any) => void;

const channelListeners = new Map<string, Set<Listener>>();

function on(channel: string, cb: Listener): () => void {
  if (!channelListeners.has(channel)) channelListeners.set(channel, new Set());
  const set = channelListeners.get(channel)!;
  set.add(cb);
  return () => set.delete(cb);
}

(window as any).__jarvisPush = (channel: string, payload: any) => {
  channelListeners.get(channel)?.forEach((cb) => cb(payload));
};

function callApi<T = any>(name: string, ...args: any[]): Promise<T> {
  return new Promise((resolve, reject) => {
    const invoke = () => {
      const api = (window as any).pywebview?.api;
      if (!api || typeof api[name] !== "function") {
        reject(new Error(`Bridge method "${name}" is not exposed by the Python backend.`));
        return;
      }
      api[name](...args).then(resolve).catch(reject);
    };
    if ((window as any).pywebview?.api) invoke();
    else window.addEventListener("pywebviewready", invoke, { once: true });
  });
}

const jarvis = {
  stats: {
    subscribe: () => callApi("stats_subscribe"),
    onUpdate: (cb: Listener) => on("stats_update", cb),
    onInternetStatus: (cb: Listener) => on("internet_status", cb),
  },
  chat: {
    getHistory: () => callApi("chat_get_history"),
    clearHistory: () => callApi("chat_clear_history"),
    providerStatus: () => callApi("provider_status"),
    onMessage: (cb: Listener) => on("chat_message", cb),
    onDelta: (cb: Listener) => on("chat_delta", cb),
    onDone: (cb: Listener) => on("chat_done", cb),
    onError: (cb: Listener) => on("chat_error", cb),
  },
  orchestrator: {
    handleText: (text: string) => callApi("orchestrator_handle_text", text),
    confirmPending: () => callApi("orchestrator_confirm_pending"),
    cancelPending: () => callApi("orchestrator_cancel_pending"),
    interrupt: () => callApi("orchestrator_interrupt"),
    analyzeScreen: (question?: string) => callApi("orchestrator_analyze_screen", question),
    onConfirmationRequired: (cb: Listener) => on("confirmation_required", cb),
    onThought: (cb: Listener) => on("thought", cb),
  },
  voice: {
    listenOnce: () => callApi("voice_listen_once"),
    listElevenLabsVoices: () => callApi<Array<{ id: string; name: string; accent: string }>>("voice_list_elevenlabs_voices"),
    onListeningChange: (cb: Listener) => on("voice_listening_change", cb),
    onWakeTriggered: (cb: Listener) => on("voice_wake_triggered", cb),
    onSpeakingChange: (cb: Listener) => on("voice_speaking_change", cb),
  },
  memory: {
    setPassphrase: (pass: string) => callApi("memory_set_passphrase", pass),
    unlock: (pass: string) => callApi("memory_unlock", pass),
    lock: () => callApi("memory_lock"),
    remember: (key: string, value: string) => callApi("memory_remember", key, value),
    recall: () => callApi("memory_recall"),
  },
  commands: {
    parse: (raw: string) => callApi("commands_parse", raw),
  },
  settings: {
    get: () => callApi("settings_get"),
    set: (partial: Record<string, unknown>) => callApi("settings_set", partial),
    setApiKeys: (partial: Record<string, string>) => callApi("api_keys_set", partial),
    getMaskedApiKeys: () => callApi("api_keys_get_masked"),
  },
  screen: {
    capture: () => callApi<string>("screen_capture"),
    ocr: () => callApi<string>("screen_ocr"),
    toggleMonitor: (enabled: boolean) => callApi("screen_toggle_monitor", enabled),
  },
  data: {
    weather: (location?: string) => callApi("data_weather", location),
    news: () => callApi("data_news"),
    stock: (symbol: string) => callApi("data_stock", symbol),
    crypto: (symbol: string) => callApi("data_crypto", symbol),
    remindersList: () => callApi("reminders_list"),
    remindersAdd: (text: string, dueAt: number) => callApi("reminders_add", text, dueAt),
    remindersToggle: (id: string) => callApi("reminders_toggle", id),
    calendarList: () => callApi("calendar_list"),
  },
  notifications: {
    onNotify: (cb: Listener) => on("notification", cb),
  },
  window: {
    minimize: () => callApi("window_minimize"),
    close: () => callApi("window_close"),
  },
};

(window as any).jarvis = jarvis;

export type JarvisBridge = typeof jarvis;
