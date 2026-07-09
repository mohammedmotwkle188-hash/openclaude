import { useEffect, useState } from "react";
import { HudPanel } from "../common/HudPanel";
import { StatMeter } from "../common/StatMeter";
import { useJarvisStore } from "../../state/store";

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export function LeftPanel() {
  const stats = useJarvisStore((s) => s.stats);
  const online = useJarvisStore((s) => s.online);
  const now = useClock();

  const time = now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const date = now.toLocaleDateString("en-GB", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });

  return (
    <div className="flex h-full w-full flex-col gap-3 overflow-y-auto pr-1">
      <HudPanel title="Chronometer">
        <div className="font-mono text-3xl font-semibold text-hud-white text-glow">{time}</div>
        <div className="mt-1 font-mono text-[11px] uppercase tracking-wide text-hud-cyan/70">{date}</div>
      </HudPanel>

      <HudPanel title="System Vitals">
        <StatMeter label="CPU" value={stats ? `${stats.cpu.loadPercent}%` : "—"} percent={stats?.cpu.loadPercent ?? 0} danger={(stats?.cpu.loadPercent ?? 0) > 85} />
        <StatMeter label="RAM" value={stats ? `${stats.ram.usedGb}/${stats.ram.totalGb} GB` : "—"} percent={stats?.ram.usedPercent ?? 0} danger={(stats?.ram.usedPercent ?? 0) > 85} />
        <StatMeter
          label="GPU"
          value={stats?.gpu.loadPercent != null ? `${stats.gpu.loadPercent}%` : "N/A"}
          percent={stats?.gpu.loadPercent ?? 0}
        />
        <StatMeter
          label="Battery"
          value={stats?.battery.hasBattery ? `${stats.battery.percent}%${stats.battery.isCharging ? " ⚡" : ""}` : "N/A"}
          percent={stats?.battery.percent ?? 100}
          danger={!!stats?.battery.hasBattery && !stats?.battery.isCharging && stats.battery.percent < 20}
        />
        <StatMeter
          label="Storage"
          value={stats ? `${stats.storage.usedGb}/${stats.storage.totalGb} GB` : "—"}
          percent={stats?.storage.usedPercent ?? 0}
          danger={(stats?.storage.usedPercent ?? 0) > 90}
        />
      </HudPanel>

      <HudPanel title="Network">
        <div className="flex items-center justify-between font-mono text-[11px]">
          <span className="text-hud-white/70">Status</span>
          <span className={online ? "text-hud-cyan text-glow" : "text-hud-orange text-glow-orange"}>
            {online ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between font-mono text-[11px]">
          <span className="text-hud-white/70">Down / Up</span>
          <span className="text-hud-white">{stats ? `${stats.network.downKbps} / ${stats.network.upKbps} KB/s` : "—"}</span>
        </div>
        <div className="mt-1.5 flex items-center justify-between font-mono text-[11px]">
          <span className="text-hud-white/70">Interface</span>
          <span className="text-hud-white/80">{stats?.network.interface ?? "—"}</span>
        </div>
      </HudPanel>

      <HudPanel title="Thermal / Processes">
        <div className="flex items-center justify-between font-mono text-[11px]">
          <span className="text-hud-white/70">CPU Temp</span>
          <span className={(stats?.temperature.cpuC ?? 0) > 80 ? "text-hud-orange text-glow-orange" : "text-hud-cyan text-glow"}>
            {stats?.temperature.cpuC != null ? `${stats.temperature.cpuC}°C` : "N/A"}
          </span>
        </div>
        <div className="mt-1.5 flex items-center justify-between font-mono text-[11px]">
          <span className="text-hud-white/70">Processes</span>
          <span className="text-hud-white">{stats ? `${stats.processes.running}/${stats.processes.total}` : "—"}</span>
        </div>
        <div className="mt-2 space-y-1">
          {stats?.processes.topByCpu.slice(0, 4).map((p) => (
            <div key={p.name} className="flex items-center justify-between font-mono text-[10px] text-hud-white/60">
              <span className="truncate">{p.name}</span>
              <span>{p.cpuPercent}%</span>
            </div>
          ))}
        </div>
      </HudPanel>
    </div>
  );
}
