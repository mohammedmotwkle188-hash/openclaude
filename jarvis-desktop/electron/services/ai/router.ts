import type { AiProviderId, ProviderStatus } from "../../../shared/types";
import type { AiAdapter, ChatTurn } from "./types";
import { JARVIS_SYSTEM_PROMPT } from "./types";
import { createAnthropicAdapter } from "./anthropic";
import { createOpenAiAdapter } from "./openai";
import { createGeminiAdapter } from "./gemini";
import { createOllamaAdapter } from "./ollama";
import { getSettings } from "../../store";

const adapters: Record<AiProviderId, AiAdapter> = {
  anthropic: createAnthropicAdapter(),
  openai: createOpenAiAdapter(),
  gemini: createGeminiAdapter(),
  ollama: createOllamaAdapter(),
};

export async function getProviderStatuses(): Promise<ProviderStatus[]> {
  const order = getSettings().providerOrder;
  return Promise.all(
    order.map(async (id) => {
      const adapter = adapters[id];
      const configured = adapter.isConfigured();
      const reachable = configured ? await adapter.isReachable().catch(() => false) : null;
      return { id, configured, reachable };
    }),
  );
}

/**
 * Streams a chat response, walking the configured provider fallback order and
 * retrying with the next provider if one fails before producing any tokens.
 */
export async function streamWithFallback(
  turns: ChatTurn[],
  onDelta: (text: string, provider: AiProviderId) => void,
  signal: AbortSignal,
  memoryContext?: string,
): Promise<AiProviderId> {
  const order = getSettings().providerOrder;
  const systemPrompt = memoryContext ? `${JARVIS_SYSTEM_PROMPT}\n\nKnown facts about the user:\n${memoryContext}` : JARVIS_SYSTEM_PROMPT;

  return runFallback(turns, systemPrompt, signal, onDelta);
}

/** Non-streaming convenience wrapper — collects the full response text from whichever provider answers. */
export async function completeOnce(
  turns: ChatTurn[],
  systemPrompt: string,
): Promise<{ text: string; provider: AiProviderId }> {
  let full = "";
  const controller = new AbortController();
  const provider = await runFallback(turns, systemPrompt, controller.signal, (delta) => {
    full += delta;
  });
  return { text: full, provider };
}

async function runFallback(
  turns: ChatTurn[],
  systemPrompt: string,
  signal: AbortSignal,
  onDelta: (text: string, provider: AiProviderId) => void,
): Promise<AiProviderId> {
  const order = getSettings().providerOrder;
  let lastError = "No AI providers are configured. Add an API key in Settings, or run a local Ollama model.";
  for (const id of order) {
    const adapter = adapters[id];
    if (!adapter.isConfigured()) continue;
    let producedAny = false;
    let errorMsg: string | null = null;
    try {
      await adapter.streamChat(turns, systemPrompt, {
        signal,
        onDelta: (text) => {
          producedAny = true;
          onDelta(text, id);
        },
        onDone: () => {},
        onError: (msg) => {
          errorMsg = msg;
        },
      });
    } catch (err: any) {
      errorMsg = err?.message ?? String(err);
    }
    if (producedAny) return id;
    if (errorMsg) lastError = errorMsg;
    if (signal.aborted) return id;
  }
  throw new Error(lastError);
}
