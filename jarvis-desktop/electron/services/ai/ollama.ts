import type { AiAdapter, ChatTurn, StreamHandlers } from "./types";
import { getSettings } from "../../store";

export function createOllamaAdapter(): AiAdapter {
  return {
    id: "ollama",
    isConfigured() {
      return true; // local, no API key required
    },
    async isReachable() {
      try {
        const base = getSettings().ollamaBaseUrl;
        const res = await fetch(`${base}/api/tags`, { signal: AbortSignal.timeout(1500) });
        return res.ok;
      } catch {
        return false;
      }
    },
    async streamChat(turns: ChatTurn[], systemPrompt: string, handlers: StreamHandlers) {
      const base = getSettings().ollamaBaseUrl;
      try {
        const res = await fetch(`${base}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: handlers.signal,
          body: JSON.stringify({
            model: "llama3.1",
            stream: true,
            messages: [
              { role: "system", content: systemPrompt },
              ...turns
                .filter((t) => t.role !== "system")
                .map((t) => ({ role: t.role, content: t.text, ...(t.image ? { images: [t.image.base64] } : {}) })),
            ],
          }),
        });
        if (!res.ok || !res.body) throw new Error(`Ollama responded with ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            const json = JSON.parse(line);
            if (json.message?.content) handlers.onDelta(json.message.content);
          }
        }
        handlers.onDone();
      } catch (err: any) {
        if (handlers.signal.aborted) return handlers.onDone();
        handlers.onError(err?.message ?? "Ollama request failed — is `ollama serve` running?");
      }
    },
  };
}
