import { useEffect } from "react";
import { useJarvisStore } from "../state/store";

/** Wires every Python -> UI push event to the zustand store. Call once, near the app root. */
export function useBridgeEvents() {
  const appendMessage = useJarvisStore((s) => s.appendMessage);
  const appendDeltaToMessage = useJarvisStore((s) => s.appendDeltaToMessage);
  const markMessageDone = useJarvisStore((s) => s.markMessageDone);
  const markMessageError = useJarvisStore((s) => s.markMessageError);
  const pushThought = useJarvisStore((s) => s.pushThought);
  const pushNotification = useJarvisStore((s) => s.pushNotification);
  const setPendingConfirmation = useJarvisStore((s) => s.setPendingConfirmation);
  const setListening = useJarvisStore((s) => s.setListening);
  const setSpeaking = useJarvisStore((s) => s.setSpeaking);
  const setWakeActive = useJarvisStore((s) => s.setWakeActive);

  useEffect(() => {
    const offs = [
      window.jarvis.chat.onMessage(appendMessage),
      window.jarvis.chat.onDelta((c: { id: string; delta: string }) => appendDeltaToMessage(c.id, c.delta)),
      window.jarvis.chat.onDone((c: { id: string; provider?: string }) => markMessageDone(c.id, c.provider)),
      window.jarvis.chat.onError((c: { id: string; error: string }) => markMessageError(c.id, c.error)),
      window.jarvis.orchestrator.onThought((t: { text: string }) => pushThought(t.text)),
      window.jarvis.orchestrator.onConfirmationRequired(setPendingConfirmation),
      window.jarvis.notifications.onNotify(pushNotification),
      window.jarvis.voice.onListeningChange(setListening),
      window.jarvis.voice.onSpeakingChange(setSpeaking),
      window.jarvis.voice.onWakeTriggered(() => {
        setWakeActive(true);
        setTimeout(() => setWakeActive(false), 2000);
      }),
    ];
    return () => offs.forEach((off) => off());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
