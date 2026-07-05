import Anthropic from "@anthropic-ai/sdk";
import type { AiAdapter, ChatTurn, StreamHandlers } from "./types";
import { getApiKey } from "../../store";

export function createAnthropicAdapter(): AiAdapter {
  return {
    id: "anthropic",
    isConfigured() {
      return !!getApiKey("anthropic");
    },
    async isReachable() {
      return this.isConfigured();
    },
    async streamChat(turns: ChatTurn[], systemPrompt: string, handlers: StreamHandlers) {
      const apiKey = getApiKey("anthropic");
      if (!apiKey) throw new Error("Anthropic API key not configured");
      const client = new Anthropic({ apiKey });
      try {
        const stream = client.messages.stream(
          {
            model: "claude-sonnet-4-5",
            max_tokens: 2048,
            system: systemPrompt,
            messages: turns
              .filter((t) => t.role !== "system")
              .map((t) => ({
                role: t.role === "assistant" ? ("assistant" as const) : ("user" as const),
                content: t.image
                  ? [
                      { type: "image" as const, source: { type: "base64" as const, media_type: t.image.mimeType as any, data: t.image.base64 } },
                      { type: "text" as const, text: t.text },
                    ]
                  : t.text,
              })),
          },
          { signal: handlers.signal },
        );
        stream.on("text", (delta) => handlers.onDelta(delta));
        await stream.finalMessage();
        handlers.onDone();
      } catch (err: any) {
        if (handlers.signal.aborted) return handlers.onDone();
        handlers.onError(err?.message ?? "Anthropic request failed");
      }
    },
  };
}
