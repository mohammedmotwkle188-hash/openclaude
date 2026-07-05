import { useEffect, useState } from "react";
import { useJarvisStore } from "../../state/store";
import type { ProviderStatus } from "../../../shared/types";

export function TopBar() {
  const stats = useJarvisStore((s) => s.stats);
  const online = useJarvisStore((s) => s.online);
  const isListening = useJarvisStore((s) => s.isListening);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    const providerId = setInterval(() => window.jarvis.chat.providerStatus().then(setProviders), 5000);
    window.jarvis.chat.providerStatus().then(setProviders);
    return () => {
      clearInterval(id);
      clearInterval(providerId);
    };
  }, []);

  const activeProvider = providers.find((p) => p.configured)?.id ?? "none";
  const aiOnline = providers.some((p) => p.configured);

  return (
    <div className="drag hud-panel flex items-center justify-between rounded-md px-4 py-2 text-[11px]">
      <div className="flex items-center gap-5 font-mono uppercase tracking-widest">
        <StatusDot label="AI" ok={aiOnline} />
        <StatusDot label="MIC" ok={isListening} />
        <StatusDot label="NET" ok={online} />
        <span className="text-hud-white/50">
          CPU <span className="text-hud-cyan">{stats?.cpu.loadPercent ?? "—"}%</span>
        </span>
        <span className="text-hud-white/50">
          RAM <span className="text-hud-cyan">{stats?.ram.usedPercent ?? "—"}%</span>
        </span>
        {stats?.battery.hasBattery && (
          <span className="text-hud-white/50">
            BATT <span className="text-hud-cyan">{stats.battery.percent}%</span>
          </span>
        )}
        <span className="text-hud-white/50">
          MODEL <span className="text-hud-cyan">{activeProvider.toUpperCase()}</span>
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="font-mono tracking-widest text-hud-white/70">
          {now.toLocaleTimeString("en-GB", { hour12: false })}
        </span>
        <div className="no-drag flex items-center gap-1.5">
          <button onClick={() => window.jarvis.window.minimize()} className="h-2.5 w-2.5 rounded-full bg-hud-cyan/40 hover:bg-hud-cyan" />
          <button onClick={() => window.jarvis.window.close()} className="h-2.5 w-2.5 rounded-full bg-hud-orange/50 hover:bg-hud-orange" />
        </div>
      </div>
    </div>
  );
}

function StatusDot({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-hud-cyan shadow-glow animate-pulseGlow" : "bg-hud-orange/70"}`} />
      <span className={ok ? "text-hud-cyan/80" : "text-hud-orange/80"}>{label}</span>
    </span>
  );
}
