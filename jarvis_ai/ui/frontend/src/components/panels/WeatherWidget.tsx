import { useEffect, useState } from "react";
import type { WeatherSnapshot } from "../../../shared/types";

export function WeatherWidget() {
  const [weather, setWeather] = useState<WeatherSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    window.jarvis.data
      .weather()
      .then((w) => !cancelled && setWeather(w))
      .catch((err) => !cancelled && setError(err?.message ?? "Weather unavailable"));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="font-mono text-[11px] text-hud-white/40">{error}</div>;
  if (!weather) return <div className="font-mono text-[11px] text-hud-white/40">Loading weather…</div>;

  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="font-hud text-2xl font-semibold text-hud-white text-glow">{weather.tempC}°C</div>
        <div className="font-mono text-[10px] uppercase tracking-wide text-hud-cyan/70">{weather.condition}</div>
      </div>
      <div className="text-right font-mono text-[11px] text-hud-white/60">
        <div>{weather.location}</div>
        <div>{weather.humidityPercent}% humidity</div>
      </div>
    </div>
  );
}
