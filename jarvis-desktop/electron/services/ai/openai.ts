import OpenAI from "openai";
import type { AiAdapter, ChatTurn, StreamHandlers } from "./types";
import { getApiKey } from "../../store";

export function createOpenAiAdapter(): AiAdapter {
  return {
    id: "openai",
    isConfigured() {
      return !!getApiKey("openai");
    },
    async isReachable() {
      return this.isConfigured();
    },
    async streamChat(turns: ChatTurn[], systemPrompt: string, handlers: StreamHandlers) {
      const apiKey = getApiKey("openai");
      if (!apiKey) throw new Error("OpenAI API key not configured");
      const client = new OpenAI({ apiKey });
      try {
        const stream = await client.chat.completions.create(
          {
            model: "gpt-4.1",
            stream: true,
            messages: [
              { role: "system", content: systemPrompt },
              ...turns
                .filter((t) => t.role !== "system")
                .map((t) => ({
                  role: t.role as "user" | "assistant",
                  content: t.image
                    ? ([
                        { type: "text", text: t.text },
                        { type: "image_url", image_url: { url: `data:${t.image.mimeType};base64,${t.image.base64}` } },
                      ] as any)
                    : t.text,
                })),
            ],
          },
          { signal: handlers.signal },
        );
        for await (const chunk of stream) {
          const delta = chunk.choices[0]?.delta?.content;
          if (delta) handlers.onDelta(delta);
        }
        handlers.onDone();
      } catch (err: any) {
        if (handlers.signal.aborted) return handlers.onDone();
        handlers.onError(err?.message ?? "OpenAI request failed");
      }
    },
  };
}
