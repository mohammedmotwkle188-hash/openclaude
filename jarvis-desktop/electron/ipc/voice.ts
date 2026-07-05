import { ipcMain } from "electron";
import { IPC } from "../../shared/types";
import { synthesizeSpeech, listVoices } from "../services/voice/elevenlabs";

export function registerVoiceIpc() {
  ipcMain.handle(IPC.voiceElevenLabsSpeak, async (_evt, text: string, voiceId?: string | null) => {
    const buffer = await synthesizeSpeech(text, voiceId);
    return { base64: buffer.toString("base64") };
  });

  ipcMain.handle(IPC.voiceElevenLabsListVoices, () => listVoices());
}
