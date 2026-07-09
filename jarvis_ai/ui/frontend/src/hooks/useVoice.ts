// Voice recognition/synthesis both run in Python now (voice/stt.py, voice/tts.py,
// voice/wakeword.py) — most native webviews (WKWebView on macOS, WebKitGTK on Linux)
// don't implement the browser SpeechRecognition API at all, so driving STT from Python
// via the real system microphone is both more correct and more portable than relying on
// in-page Web Speech APIs. This hook is now just a thin call into the bridge; listening/
// speaking/wake-word state arrives via push events wired in useBridgeEvents. The Python
// side starts/stops its own wake-word thread whenever settings.wakeWordEnabled changes
// (see ui/dashboard.py's settings_set), so there's nothing to enable/disable from here.

export function useVoice() {
  const listenOnce = () => {
    window.jarvis.voice.listenOnce().catch(() => {
      // Errors (no mic, recognition service unreachable) surface as a notification/thought
      // pushed from Python — nothing extra to do here.
    });
  };

  return { listenOnce, supported: true };
}
