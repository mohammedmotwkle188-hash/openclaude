import { motion } from "framer-motion";
import { useJarvisStore } from "../../state/store";

interface RadarProps {
  animationsEnabled: boolean;
}

export function Radar({ animationsEnabled }: RadarProps) {
  const isSpeaking = useJarvisStore((s) => s.isSpeaking);
  const isListening = useJarvisStore((s) => s.isListening);
  const wakeActive = useJarvisStore((s) => s.wakeActive);
  const active = isSpeaking || isListening || wakeActive;

  return (
    <div className="relative flex items-center justify-center" style={{ width: "min(58vh, 620px)", height: "min(58vh, 620px)" }}>
      {/* outer static rings */}
      <div className="absolute inset-0 rounded-full border border-hud-cyan/20" />
      <div className="absolute inset-[4%] rounded-full border border-hud-cyan/15" />

      {/* rotating ring 1: tick marks */}
      <div className={`absolute inset-[8%] rounded-full border border-dashed border-hud-cyan/40 ${animationsEnabled ? "animate-spin-slow" : ""}`} />

      {/* rotating ring 2: reverse */}
      <div className={`absolute inset-[16%] rounded-full border-2 border-hud-blue/30 ${animationsEnabled ? "animate-spin-slow-rev" : ""}`}>
        <div className="absolute -top-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full bg-hud-cyan shadow-glow" />
      </div>

      {/* rotating ring 3: arc segments */}
      <svg className={`absolute inset-[24%] ${animationsEnabled ? "animate-spin-slower" : ""}`} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="47" fill="none" stroke="rgba(63,240,255,0.35)" strokeWidth="1.5" strokeDasharray="16 10" />
      </svg>

      {/* radar sweep */}
      {animationsEnabled && (
        <div
          className="absolute inset-[8%] rounded-full animate-sweep"
          style={{
            background: "conic-gradient(from 0deg, rgba(63,240,255,0.35), transparent 25%)",
            maskImage: "radial-gradient(circle, transparent 0%, black 70%)",
            WebkitMaskImage: "radial-gradient(circle, transparent 0%, black 70%)",
          }}
        />
      )}

      {/* periodic scan pulse */}
      {animationsEnabled && (
        <motion.div
          className="absolute inset-[8%] rounded-full border border-hud-cyan/60"
          animate={{ scale: [0.4, 1.15], opacity: [0.9, 0] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "easeOut" }}
        />
      )}

      {/* grid crosshair */}
      <div className="absolute inset-[8%] rounded-full opacity-30" style={{
        backgroundImage: "linear-gradient(rgba(63,240,255,0.25) 1px, transparent 1px), linear-gradient(90deg, rgba(63,240,255,0.25) 1px, transparent 1px)",
        backgroundSize: "20% 20%",
        maskImage: "radial-gradient(circle, black 70%, transparent 100%)",
        WebkitMaskImage: "radial-gradient(circle, black 70%, transparent 100%)",
      }} />

      {/* center orb */}
      <div className="relative z-10 flex flex-col items-center justify-center">
        <motion.div
          className={`h-28 w-28 rounded-full ${active ? "shadow-glowOrange" : "shadow-glow"}`}
          style={{
            background: active
              ? "radial-gradient(circle at 35% 30%, #fff, #ff8a3d 40%, #7a3f14 90%)"
              : "radial-gradient(circle at 35% 30%, #fff, #3ff0ff 40%, #0e6b78 90%)",
          }}
          animate={animationsEnabled ? { scale: [1, 1.06, 1] } : {}}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
        <div className="mt-6 text-center">
          <div className="font-hud text-2xl font-bold tracking-[0.35em] text-hud-white text-glow">J.A.R.V.I.S</div>
          <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.3em] text-hud-cyan/70">
            Artificial Intelligence System
          </div>
        </div>
      </div>
    </div>
  );
}
