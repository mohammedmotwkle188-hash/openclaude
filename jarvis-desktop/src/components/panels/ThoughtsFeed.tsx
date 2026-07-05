import { useJarvisStore } from "../../state/store";

export function ThoughtsFeed() {
  const thoughts = useJarvisStore((s) => s.thoughts);
  return (
    <div className="flex h-full flex-col gap-1.5 overflow-y-auto pr-1 font-mono text-[11px]">
      {thoughts.length === 0 && <div className="text-hud-white/40">No activity yet.</div>}
      {[...thoughts].reverse().map((t) => (
        <div key={t.id} className="flex gap-2 text-hud-cyan/80">
          <span className="text-hud-cyan/40">{new Date(t.timestamp).toLocaleTimeString("en-GB", { hour12: false })}</span>
          <span className="text-hud-white/70">{t.text}</span>
        </div>
      ))}
    </div>
  );
}
