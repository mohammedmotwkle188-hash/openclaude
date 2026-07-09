import { useEffect, useRef } from "react";
import { useJarvisStore } from "../../state/store";

export function ChatHistory() {
  const messages = useJarvisStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.text]);

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto pr-1">
      {messages.length === 0 && (
        <div className="mt-4 text-center font-mono text-[11px] text-hud-white/40">
          Say "Jarvis" or type a command below to begin.
        </div>
      )}
      {messages.map((m) => (
        <div key={m.id} className={`max-w-[92%] rounded px-2.5 py-1.5 text-[12.5px] leading-snug ${
          m.role === "user" ? "self-end bg-hud-blue/15 border border-hud-blue/30 text-hud-white" : "self-start bg-hud-cyan/10 border border-hud-cyan/25 text-hud-white"
        }`}>
          <div className="mb-0.5 font-mono text-[9px] uppercase tracking-widest text-hud-cyan/60">
            {m.role === "user" ? "You" : m.provider ? `Jarvis · ${m.provider}` : "Jarvis"}
          </div>
          {m.text || (m.pending ? <span className="inline-flex gap-1"><Dot /><Dot delay="150ms" /><Dot delay="300ms" /></span> : "")}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return <span className="h-1.5 w-1.5 animate-pulseGlow rounded-full bg-hud-cyan" style={{ animationDelay: delay }} />;
}
