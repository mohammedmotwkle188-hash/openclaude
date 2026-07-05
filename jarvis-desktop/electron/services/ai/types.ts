import type { AiProviderId, ImageAttachment } from "../../../shared/types";

export interface ChatTurn {
  role: "user" | "assistant" | "system";
  text: string;
  image?: ImageAttachment;
}

export interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
  signal: AbortSignal;
}

export interface AiAdapter {
  id: AiProviderId;
  isConfigured(): boolean;
  isReachable(): Promise<boolean>;
  streamChat(turns: ChatTurn[], systemPrompt: string, handlers: StreamHandlers): Promise<void>;
}

export const JARVIS_SYSTEM_PROMPT = `You are J.A.R.V.I.S., a calm, precise, and dryly witty AI assistant running locally on the user's desktop.
Speak with understated confidence and British phrasing. Keep spoken responses concise (2-4 sentences) unless the user
asks for detail, code, or a document — then be thorough. Address the user respectfully. You can control the desktop,
read the screen, manage files, and answer questions using your knowledge and any provided context. Never fabricate
system state; if you don't have live data, say so plainly.`;
