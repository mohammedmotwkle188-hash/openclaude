import type { ElevenLabsVoice } from "../../../shared/types";
import { getApiKey } from "../../store";

// Warm, resonant British male "George" — ElevenLabs' own quickstart-docs example voice.
// Verify it still sounds right in Settings once you add a key; their voice library can
// change, and this ID isn't something that could be verified from the build environment.
export const DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb";

export function isElevenLabsConfigured(): boolean {
  return !!getApiKey("elevenlabs");
}

export async function synthesizeSpeech(text: string, voiceId?: string | null): Promise<Buffer> {
  const apiKey = getApiKey("elevenlabs");
  if (!apiKey) throw new Error("No ElevenLabs API key configured");

  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId || DEFAULT_ELEVENLABS_VOICE_ID}`, {
    method: "POST",
    headers: { "xi-api-key": apiKey, "Content-Type": "application/json", Accept: "audio/mpeg" },
    body: JSON.stringify({
      text,
      model_id: "eleven_multilingual_v2",
      voice_settings: { stability: 0.5, similarity_boost: 0.75 },
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`ElevenLabs TTS failed (${res.status}): ${detail.slice(0, 200)}`);
  }

  return Buffer.from(await res.arrayBuffer());
}

export async function listVoices(): Promise<ElevenLabsVoice[]> {
  const apiKey = getApiKey("elevenlabs");
  if (!apiKey) throw new Error("Add an ElevenLabs API key in Settings first.");

  const res = await fetch("https://api.elevenlabs.io/v1/voices", { headers: { "xi-api-key": apiKey } });
  if (!res.ok) throw new Error(`Couldn't fetch ElevenLabs voices (${res.status})`);

  const data = (await res.json()) as { voices?: Array<{ voice_id: string; name: string; labels?: { accent?: string } }> };
  return (data.voices ?? []).map((v) => ({ id: v.voice_id, name: v.name, accent: v.labels?.accent ?? "" }));
}
