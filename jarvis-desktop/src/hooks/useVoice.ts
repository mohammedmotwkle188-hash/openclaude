import { useEffect, useRef } from "react";
import { useJarvisStore } from "../state/store";
import { VoiceEngine } from "../lib/voice/voiceEngine";
import { dispatchUserInput } from "../lib/commands/dispatch";
import { interruptSpeech } from "../lib/voice/tts";

export function useVoice() {
  const settings = useJarvisStore((s) => s.settings);
  const setTranscript = useJarvisStore((s) => s.setTranscript);
  const setListening = useJarvisStore((s) => s.setListening);
  const setWakeActive = useJarvisStore((s) => s.setWakeActive);
  const engineRef = useRef<VoiceEngine | null>(null);

  useEffect(() => {
    if (!VoiceEngine.isSupported()) return;
    engineRef.current = new VoiceEngine({
      onInterim: (text) => setTranscript(text),
      onCommand: (text) => {
        setTranscript(text);
        interruptSpeech();
        dispatchUserInput(text);
      },
      onWakeTriggered: () => {
        setWakeActive(true);
        setTimeout(() => setWakeActive(false), 2000);
      },
      onListeningChange: setListening,
    });

    return () => {
      engineRef.current?.disable();
      engineRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!settings || !engineRef.current) return;
    if (settings.wakeWordEnabled) {
      engineRef.current.enableWakeWord();
    } else {
      engineRef.current.disable();
    }
  }, [settings?.wakeWordEnabled]);

  const listenOnce = () => {
    engineRef.current?.listenOnce();
  };

  return { listenOnce, supported: VoiceEngine.isSupported() };
}
