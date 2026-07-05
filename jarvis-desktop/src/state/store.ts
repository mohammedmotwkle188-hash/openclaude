import { create } from "zustand";
import type {
  AppSettings,
  ChatMessage,
  NotificationItem,
  ParsedCommand,
  SystemStatsSnapshot,
} from "../../shared/types";

interface AssistantThoughtLine {
  id: string;
  text: string;
  timestamp: number;
}

interface JarvisState {
  stats: SystemStatsSnapshot | null;
  online: boolean;

  settings: AppSettings | null;
  setSettings: (s: AppSettings) => void;

  messages: ChatMessage[];
  setMessages: (m: ChatMessage[]) => void;
  appendMessage: (m: ChatMessage) => void;
  updateLastAssistant: (delta: string) => void;

  thoughts: AssistantThoughtLine[];
  pushThought: (text: string) => void;

  notifications: NotificationItem[];
  pushNotification: (n: NotificationItem) => void;

  transcript: string;
  setTranscript: (t: string) => void;

  isListening: boolean;
  setListening: (v: boolean) => void;
  isSpeaking: boolean;
  setSpeaking: (v: boolean) => void;
  wakeActive: boolean;
  setWakeActive: (v: boolean) => void;

  activeRequestId: string | null;
  setActiveRequestId: (id: string | null) => void;

  pendingConfirmation: ParsedCommand | null;
  setPendingConfirmation: (cmd: ParsedCommand | null) => void;

  setStats: (s: SystemStatsSnapshot) => void;
  setOnline: (v: boolean) => void;
}

export const useJarvisStore = create<JarvisState>((set) => ({
  stats: null,
  online: true,

  settings: null,
  setSettings: (s) => set({ settings: s }),

  messages: [],
  setMessages: (m) => set({ messages: m }),
  appendMessage: (m) => set((state) => ({ messages: [...state.messages, m] })),
  updateLastAssistant: (delta) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant" && last.pending) {
        msgs[msgs.length - 1] = { ...last, text: last.text + delta };
      }
      return { messages: msgs };
    }),

  thoughts: [],
  pushThought: (text) =>
    set((state) => ({
      thoughts: [...state.thoughts.slice(-24), { id: crypto.randomUUID(), text, timestamp: Date.now() }],
    })),

  notifications: [],
  pushNotification: (n) => set((state) => ({ notifications: [n, ...state.notifications].slice(0, 30) })),

  transcript: "",
  setTranscript: (t) => set({ transcript: t }),

  isListening: false,
  setListening: (v) => set({ isListening: v }),
  isSpeaking: false,
  setSpeaking: (v) => set({ isSpeaking: v }),
  wakeActive: false,
  setWakeActive: (v) => set({ wakeActive: v }),

  activeRequestId: null,
  setActiveRequestId: (id) => set({ activeRequestId: id }),

  pendingConfirmation: null,
  setPendingConfirmation: (cmd) => set({ pendingConfirmation: cmd }),

  setStats: (s) => set({ stats: s }),
  setOnline: (v) => set({ online: v }),
}));
