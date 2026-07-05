interface StatMeterProps {
  label: string;
  value: string;
  percent: number;
  danger?: boolean;
}

export function StatMeter({ label, value, percent, danger }: StatMeterProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const color = danger ? "bg-hud-orange" : "bg-hud-cyan";
  return (
    <div className="mb-2.5">
      <div className="mb-1 flex items-center justify-between font-mono text-[11px] tracking-wide">
        <span className="text-hud-white/70">{label}</span>
        <span className={danger ? "text-hud-orange text-glow-orange" : "text-hud-cyan text-glow"}>{value}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
