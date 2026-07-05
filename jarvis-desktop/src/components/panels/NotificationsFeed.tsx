import { useEffect, useState } from "react";
import { useJarvisStore } from "../../state/store";
import { analyzeScreen } from "../../lib/commands/chat";

export function NotificationsFeed() {
  const notifications = useJarvisStore((s) => s.notifications);
  const pushNotification = useJarvisStore((s) => s.pushNotification);
  const [monitoring, setMonitoring] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => window.jarvis.notifications.onNotify(pushNotification), [pushNotification]);

  const toggleMonitor = async () => {
    const next = !monitoring;
    await window.jarvis.screen.toggleMonitor(next);
    setMonitoring(next);
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      await analyzeScreen();
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto pr-1">
      <div className="mb-1 flex gap-1.5">
        <button
          onClick={toggleMonitor}
          className={`no-drag self-start rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-widest ${
            monitoring ? "border-hud-orange text-hud-orange bg-hud-orange/10" : "border-hud-cyan/30 text-hud-cyan/70 hover:bg-hud-cyan/10"
          }`}
        >
          {monitoring ? "Live Screen Monitor: ON" : "Live Screen Monitor: OFF"}
        </button>
        <button
          onClick={runAnalysis}
          disabled={analyzing}
          className="no-drag self-start rounded border border-hud-cyan/30 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-hud-cyan/70 hover:bg-hud-cyan/10 disabled:opacity-40"
        >
          {analyzing ? "Analyzing…" : "Analyze Screen Now"}
        </button>
      </div>
      {notifications.length === 0 && <div className="font-mono text-[11px] text-hud-white/40">No notifications.</div>}
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`rounded border px-2 py-1.5 text-[11px] ${
            n.level === "critical"
              ? "border-hud-orange/50 bg-hud-orange/10 text-hud-orange"
              : n.level === "warning"
                ? "border-hud-orange/30 bg-hud-orange/5 text-hud-white"
                : "border-hud-cyan/25 bg-hud-cyan/5 text-hud-white/80"
          }`}
        >
          <div className="font-mono text-[9px] uppercase tracking-widest opacity-60">{n.title}</div>
          <div>{n.body}</div>
        </div>
      ))}
    </div>
  );
}
