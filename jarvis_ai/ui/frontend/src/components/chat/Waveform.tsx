import { useMicLevel } from "../../hooks/useMicLevel";
import { useJarvisStore } from "../../state/store";

export function Waveform() {
  const isListening = useJarvisStore((s) => s.isListening);
  const isSpeaking = useJarvisStore((s) => s.isSpeaking);
  const levels = useMicLevel(isListening);
  const active = isListening || isSpeaking;

  return (
    <div className="flex h-8 items-center justify-center gap-[3px]">
      {levels.map((lvl, i) => {
        const height = isSpeaking ? 30 + Math.sin(Date.now() / 120 + i) * 20 : Math.max(8, lvl * 100);
        return (
          <span
            key={i}
            className={`w-[3px] rounded-full transition-all duration-100 ${active ? "bg-hud-cyan shadow-glow" : "bg-hud-cyan/25"}`}
            style={{ height: `${Math.min(100, height)}%` }}
          />
        );
      })}
    </div>
  );
}
