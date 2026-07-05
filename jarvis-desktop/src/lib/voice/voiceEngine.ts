import type { SpeechRecognitionEventLike, SpeechRecognitionLike } from "../../types/speech";
import { interruptSpeech, isSpeaking } from "./tts";

const WAKE_WORD = /\bjarvis\b/i;

export interface VoiceEngineHandlers {
  onInterim: (text: string) => void;
  onCommand: (text: string) => void;
  onWakeTriggered: () => void;
  onListeningChange: (listening: boolean) => void;
}

type Mode = "off" | "armed" | "active";

export class VoiceEngine {
  private recognition: SpeechRecognitionLike | null = null;
  private mode: Mode = "off";
  private handlers: VoiceEngineHandlers;
  private restartGuard = false;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(handlers: VoiceEngineHandlers) {
    this.handlers = handlers;
  }

  static isSupported() {
    return typeof window !== "undefined" && !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  private buildRecognition(): SpeechRecognitionLike {
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) throw new Error("SpeechRecognition is not supported in this browser runtime.");
    const rec = new Ctor();
    rec.lang = "en-GB";
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onresult = (ev: SpeechRecognitionEventLike) => {
      if (isSpeaking()) interruptSpeech();
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const result = ev.results[i];
        const transcript = result[0].transcript;
        if (result.isFinal) {
          this.handleFinal(transcript.trim());
        } else {
          interim += transcript;
        }
      }
      if (interim) this.handlers.onInterim(interim);
    };

    rec.onerror = () => {
      // Recognition errors (no-speech, network blips) are recoverable — onend fires next
      // and the restart loop below picks it back up rather than surfacing an error to the UI.
    };

    rec.onend = () => {
      this.handlers.onListeningChange(false);
      if (this.mode !== "off" && !this.restartGuard) {
        this.restartGuard = true;
        setTimeout(() => {
          this.restartGuard = false;
          if (this.mode !== "off") this.startRecognition();
        }, 250);
      }
    };

    rec.onstart = () => this.handlers.onListeningChange(true);

    return rec;
  }

  private handleFinal(text: string) {
    if (!text) return;
    if (this.mode === "armed") {
      if (WAKE_WORD.test(text)) {
        this.handlers.onWakeTriggered();
        const remainder = text.replace(WAKE_WORD, "").trim();
        if (remainder.length > 2) {
          this.handlers.onCommand(remainder);
          this.mode = "armed";
        } else {
          this.mode = "active";
          this.armSilenceTimeout();
        }
      }
    } else if (this.mode === "active") {
      this.clearSilenceTimeout();
      this.handlers.onCommand(text);
      this.mode = this.wasWakeArmed ? "armed" : "off";
    }
  }

  private wasWakeArmed = false;

  private armSilenceTimeout() {
    this.clearSilenceTimeout();
    this.silenceTimer = setTimeout(() => {
      if (this.mode === "active") this.mode = this.wasWakeArmed ? "armed" : "off";
    }, 8000);
  }

  private clearSilenceTimeout() {
    if (this.silenceTimer) clearTimeout(this.silenceTimer);
    this.silenceTimer = null;
  }

  private startRecognition() {
    try {
      this.recognition?.start();
    } catch {
      // start() throws if already running — safe to ignore.
    }
  }

  /** Continuous wake-word listening: says "jarvis" then a command, or "jarvis" then pauses and waits. */
  enableWakeWord() {
    this.wasWakeArmed = true;
    this.mode = "armed";
    this.recognition = this.buildRecognition();
    this.startRecognition();
  }

  /** One-shot active listening triggered by the mic button, bypassing the wake word. */
  listenOnce() {
    this.wasWakeArmed = this.mode === "armed" || this.wasWakeArmed;
    this.mode = "active";
    if (!this.recognition) {
      this.recognition = this.buildRecognition();
      this.startRecognition();
    }
    this.armSilenceTimeout();
  }

  disable() {
    this.mode = "off";
    this.wasWakeArmed = false;
    this.clearSilenceTimeout();
    this.recognition?.stop();
    this.recognition = null;
  }
}
