import { useJarvisStore } from "../../state/store";
import { speak } from "../voice/tts";

let unsubscribeStream: (() => void) | null = null;

export function initChatStreamListener() {
  if (unsubscribeStream) return;
  unsubscribeStream = window.jarvis.chat.onStream((chunk) => {
    const store = useJarvisStore.getState();
    if (chunk.requestId !== store.activeRequestId) return;

    if (chunk.delta) {
      store.updateLastAssistant(chunk.delta);
    }
    if (chunk.error) {
      store.updateLastAssistant(`\n\n[${chunk.error}]`);
    }
    if (chunk.done) {
      const msgs = useJarvisStore.getState().messages;
      const last = msgs[msgs.length - 1];
      store.setActiveRequestId(null);
      if (last && last.role === "assistant") {
        useJarvisStore.setState({
          messages: msgs.map((m, i) => (i === msgs.length - 1 ? { ...m, pending: false, provider: chunk.provider } : m)),
        });
        const { settings } = useJarvisStore.getState();
        if (settings?.voiceEnabled && last.text.trim()) {
          store.setSpeaking(true);
          speak(last.text, {
            rate: settings.speechRate,
            voiceName: settings.voiceName,
            ttsProvider: settings.ttsProvider,
            elevenLabsVoiceId: settings.elevenLabsVoiceId,
          }, {
            onEnd: () => useJarvisStore.getState().setSpeaking(false),
          });
        }
      }
    }
  });
}

export async function sendChat(text: string) {
  const store = useJarvisStore.getState();
  store.pushThought(`Thinking about: "${text}"`);

  const assistantId = crypto.randomUUID();
  store.appendMessage({ id: assistantId, role: "assistant", text: "", timestamp: Date.now(), pending: true });

  const turns = [...useJarvisStore.getState().messages.filter((m) => !m.pending)];
  const requestId = await window.jarvis.chat.send(turns);
  store.setActiveRequestId(requestId);
}

export async function analyzeScreen(question = "What's currently on my screen? Describe it and answer anything notable.") {
  const store = useJarvisStore.getState();
  const image = await window.jarvis.screen.captureBase64();
  store.appendMessage({ id: crypto.randomUUID(), role: "user", text: `[screenshot attached] ${question}`, timestamp: Date.now() });
  store.pushThought("Capturing screen for visual analysis…");

  const assistantId = crypto.randomUUID();
  store.appendMessage({ id: assistantId, role: "assistant", text: "", timestamp: Date.now(), pending: true });

  const turns = useJarvisStore
    .getState()
    .messages.filter((m) => !m.pending)
    .map((m, i, arr) => (i === arr.length - 1 ? { ...m, image } : m));

  const requestId = await window.jarvis.chat.send(turns);
  store.setActiveRequestId(requestId);
}

export async function interruptChat() {
  const { activeRequestId } = useJarvisStore.getState();
  if (activeRequestId) {
    await window.jarvis.chat.interrupt(activeRequestId);
    useJarvisStore.getState().setActiveRequestId(null);
  }
}
