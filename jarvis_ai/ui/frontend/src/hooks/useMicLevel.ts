import { useEffect, useRef, useState } from "react";

/** Real mic amplitude via Web Audio, sampled independently of SpeechRecognition — drives the waveform visual. */
export function useMicLevel(active: boolean, bars = 24) {
  const [levels, setLevels] = useState<number[]>(() => Array(bars).fill(0.05));
  const rafRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!active) {
      setLevels(Array(bars).fill(0.05));
      return;
    }

    let audioCtx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let cancelled = false;

    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        audioCtx = new AudioContext();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 128;
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        const data = new Uint8Array(analyser.frequencyBinCount);

        const tick = () => {
          if (!analyser) return;
          analyser.getByteFrequencyData(data);
          const chunk = Math.floor(data.length / bars);
          const next: number[] = [];
          for (let i = 0; i < bars; i++) {
            const slice = data.slice(i * chunk, (i + 1) * chunk);
            const avg = slice.reduce((a, b) => a + b, 0) / (slice.length || 1);
            next.push(Math.max(0.05, avg / 255));
          }
          setLevels(next);
          rafRef.current = requestAnimationFrame(tick);
        };
        tick();
      })
      .catch(() => {
        // No mic permission — fall back to a gentle idle animation via CSS only.
      });

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtx?.close();
    };
  }, [active, bars]);

  return levels;
}
