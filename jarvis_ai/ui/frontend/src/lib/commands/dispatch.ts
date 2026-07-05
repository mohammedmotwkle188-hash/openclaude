// All "brain" logic (parsing, confirmation gating, execution, chat, speaking) now lives in
// Python's core/orchestrator.py — this module just forwards raw text there and lets the
// resulting chat_message / chat_delta / confirmation_required / thought / notification
// events (wired up in initBridgeListeners, called once from App.tsx) update the UI.

export async function dispatchUserInput(rawText: string) {
  const text = rawText.trim();
  if (!text) return;
  await window.jarvis.orchestrator.handleText(text);
}

export async function confirmPendingCommand() {
  await window.jarvis.orchestrator.confirmPending();
}

export async function cancelPendingCommand() {
  await window.jarvis.orchestrator.cancelPending();
}

export async function analyzeScreen(question?: string) {
  await window.jarvis.orchestrator.analyzeScreen(question);
}

export async function interruptJarvis() {
  await window.jarvis.orchestrator.interrupt();
}
