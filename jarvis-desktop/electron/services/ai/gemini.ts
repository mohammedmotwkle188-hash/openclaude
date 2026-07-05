import { GoogleGenerativeAI } from "@google/generative-ai";
import type { AiAdapter, ChatTurn, StreamHandlers } from "./types";
import { getApiKey } from "../../store";

export function createGeminiAdapter(): AiAdapter {
  return {
    id: "gemini",
    isConfigured() {
      return !!getApiKey("gemini");
    },
    async isReachable() {
      return this.isConfigured();
    },
    async streamChat(turns: ChatTurn[], systemPrompt: string, handlers: StreamHandlers) {
      const apiKey = getApiKey("gemini");
      if (!apiKey) throw new Error("Gemini API key not configured");
      const genAI = new GoogleGenerativeAI(apiKey);
      const model = genAI.getGenerativeModel({ model: "gemini-1.5-pro", systemInstruction: systemPrompt });
      try {
        const history = turns.slice(0, -1).map((t) => ({
          role: t.role === "assistant" ? "model" : "user",
          parts: [{ text: t.text }],
        }));
        const last = turns[turns.length - 1];
        const chat = model.startChat({ history });
        const lastParts = last?.image
          ? [{ text: last.text }, { inlineData: { mimeType: last.image.mimeType, data: last.image.base64 } }]
          : last?.text ?? "";
        const result = await chat.sendMessageStream(lastParts, { signal: handlers.signal });
        for await (const chunk of result.stream) {
          const text = chunk.text();
          if (text) handlers.onDelta(text);
        }
        handlers.onDone();
      } catch (err: any) {
        if (handlers.signal.aborted) return handlers.onDone();
        handlers.onError(err?.message ?? "Gemini request failed");
      }
    },
  };
}
