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

export function speak(
  text: string,
  opts: { rate?: number; voiceName?: string | null },
  handlers?: { onStart?: () => void; onEnd?: () => void },
) {
  if (!text.trim()) return;
  window.speechSynthesis.cancel();
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
}

export function isSpeaking() {
  return window.speechSynthesis.speaking;
}
