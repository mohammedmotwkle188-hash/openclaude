// Two-tier TTS: ElevenLabs (best quality, needs an API key kept in the main process — the
// renderer never sees it, just asks main to synthesize and hands back audio bytes to
// play) and the browser's built-in speechSynthesis as a free, no-key fallback. Which tier
// runs first is controlled by settings.ttsProvider ("auto" tries ElevenLabs if a key is
// configured, then falls back to the browser voice on any failure).

const BRITISH_MALE_HINTS = ["UK English Male", "Google UK English Male", "Daniel", "Arthur", "Oliver", "Ryan"];

export function pickBritishVoice(preferredName?: string | null): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  if (preferredName) {
    const exact = voices.find((v) => v.name === preferredName);
    if (exact) return exact;
  }

  for (const hint of BRITISH_MALE_HINTS) {
    const match = voices.find((v) => v.name.includes(hint) && v.lang.startsWith("en-GB"));
    if (match) return match;
  }
  const anyGbMale = voices.find((v) => v.lang.startsWith("en-GB") && /male/i.test(v.name));
  if (anyGbMale) return anyGbMale;
  const anyGb = voices.find((v) => v.lang.startsWith("en-GB"));
  return anyGb ?? voices.find((v) => v.lang.startsWith("en")) ?? voices[0] ?? null;
}

export function listBritishVoices(): SpeechSynthesisVoice[] {
  return window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith("en-GB"));
}

let currentUtterance: SpeechSynthesisUtterance | null = null;
let currentAudio: HTMLAudioElement | null = null;

interface SpeakOptions {
  rate?: number;
  voiceName?: string | null;
  ttsProvider?: "auto" | "elevenlabs" | "browser";
  elevenLabsVoiceId?: string | null;
}

export async function speak(text: string, opts: SpeakOptions, handlers?: { onStart?: () => void; onEnd?: () => void }) {
  if (!text.trim()) return;
  interruptSpeech();

  const wantsElevenLabs = opts.ttsProvider === "elevenlabs" || opts.ttsProvider === undefined || opts.ttsProvider === "auto";
  if (wantsElevenLabs) {
    try {
      const { base64 } = await window.jarvis.voice.elevenLabsSpeak(text, opts.elevenLabsVoiceId);
      playBase64Audio(base64, handlers);
      return;
    } catch {
      // No key configured, network hiccup, or bad voice id — fall through to the browser voice.
    }
  }
  speakBrowser(text, opts, handlers);
}

function playBase64Audio(base64: string, handlers?: { onStart?: () => void; onEnd?: () => void }) {
  const audio = new Audio(`data:audio/mpeg;base64,${base64}`);
  currentAudio = audio;
  audio.onplay = () => handlers?.onStart?.();
  audio.onended = () => {
    currentAudio = null;
    handlers?.onEnd?.();
  };
  audio.onerror = () => {
    currentAudio = null;
    handlers?.onEnd?.();
  };
  audio.play().catch(() => {
    currentAudio = null;
    handlers?.onEnd?.();
  });
}

function speakBrowser(text: string, opts: SpeakOptions, handlers?: { onStart?: () => void; onEnd?: () => void }) {
  const utterance = new SpeechSynthesisUtterance(text);
  const voice = pickBritishVoice(opts.voiceName);
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang ?? "en-GB";
  utterance.rate = opts.rate ?? 1.05;
  utterance.pitch = 0.95;
  utterance.onstart = () => handlers?.onStart?.();
  utterance.onend = () => {
    currentUtterance = null;
    handlers?.onEnd?.();
  };
  utterance.onerror = () => {
    currentUtterance = null;
    handlers?.onEnd?.();
  };
  currentUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

export function interruptSpeech() {
  if (currentUtterance) {
    window.speechSynthesis.cancel();
    currentUtterance = null;
  }
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
}

export function isSpeaking() {
  return window.speechSynthesis.speaking || !!currentAudio;
}
