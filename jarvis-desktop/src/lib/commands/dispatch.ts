import { useJarvisStore } from "../../state/store";
import { speak } from "../voice/tts";
import { sendChat } from "./chat";
import type { ParsedCommand } from "../../../shared/types";

const DATA_ACTIONS = new Set(["weather", "news", "stock", "crypto"]);

function say(text: string) {
  const { settings } = useJarvisStore.getState();
  useJarvisStore.getState().appendMessage({ id: crypto.randomUUID(), role: "assistant", text, timestamp: Date.now() });
  useJarvisStore.getState().pushThought(text);
  if (settings?.voiceEnabled) {
    useJarvisStore.getState().setSpeaking(true);
    speak(text, {
      rate: settings.speechRate,
      voiceName: settings.voiceName,
      ttsProvider: settings.ttsProvider,
      elevenLabsVoiceId: settings.elevenLabsVoiceId,
    }, {
      onEnd: () => useJarvisStore.getState().setSpeaking(false),
    });
  }
}

async function runDataAction(cmd: ParsedCommand) {
  try {
    if (cmd.action === "weather") {
      const w = await window.jarvis.data.weather(cmd.args.location || undefined);
      say(`It's currently ${w.tempC}°C and ${w.condition} in ${w.location}, with ${w.humidityPercent}% humidity.`);
    } else if (cmd.action === "news") {
      const headlines = await window.jarvis.data.news();
      if (!headlines.length) return say("No headlines available right now.");
      say(`Top headlines: ${headlines.slice(0, 3).map((h) => h.title).join(". ")}`);
    } else if (cmd.action === "stock") {
      say(await window.jarvis.data.stock(cmd.args.symbol));
    } else if (cmd.action === "crypto") {
      say(await window.jarvis.data.crypto(cmd.args.symbol));
    }
  } catch (err: any) {
    say(err?.message ?? "That data source isn't available right now.");
  }
}

export async function dispatchUserInput(rawText: string) {
  const text = rawText.trim();
  if (!text) return;

  useJarvisStore.getState().appendMessage({ id: crypto.randomUUID(), role: "user", text, timestamp: Date.now() });

  const parsed = await window.jarvis.commands.parse(text).catch(() => null);

  if (parsed && DATA_ACTIONS.has(parsed.action)) {
    return runDataAction(parsed);
  }

  if (parsed && parsed.risk === "confirm") {
    useJarvisStore.getState().pushThought(`Awaiting confirmation: ${parsed.label}`);
    useJarvisStore.getState().setPendingConfirmation(parsed);
    return;
  }

  if (parsed && parsed.risk === "safe") {
    const result = await window.jarvis.commands.execute(parsed);
    say(result.message);
    return;
  }

  // Not a recognized structured command — hand it to the conversational AI.
  await sendChat(text);
}

export async function confirmAndRun(cmd: ParsedCommand) {
  useJarvisStore.getState().setPendingConfirmation(null);
  const result = await window.jarvis.commands.execute(cmd);
  say(result.message);
}

export function cancelConfirmation() {
  useJarvisStore.getState().setPendingConfirmation(null);
  useJarvisStore.getState().pushThought("Confirmation cancelled.");
}
