import { useState } from "react";
import { HudPanel } from "../common/HudPanel";
import { Waveform } from "../chat/Waveform";
import { dispatchUserInput } from "../../lib/commands/dispatch";
import { useJarvisStore } from "../../state/store";
import { useSettings } from "../../hooks/useSettings";
import { useVoice } from "../../hooks/useVoice";

interface BottomPanelProps {
  onOpenSettings: () => void;
}

export function BottomPanel({ onOpenSettings }: BottomPanelProps) {
  const [input, setInput] = useState("");
  const { settings, updateSettings } = useSettings();
  const { listenOnce, supported } = useVoice();
  const isListening = useJarvisStore((s) => s.isListening);
  const isSpeaking = useJarvisStore((s) => s.isSpeaking);
  const wakeActive = useJarvisStore((s) => s.wakeActive);

  const submit = () => {
    if (!input.trim()) return;
    dispatchUserInput(input);
    setInput("");
  };

  const micActive = isListening || wakeActive;

  return (
    <HudPanel className="w-full">
      <div className="flex items-center gap-4">
        <button
          onClick={listenOnce}
          disabled={!supported}
          title={supported ? "Push to talk" : "Speech recognition unsupported in this build"}
          className={`no-drag flex h-11 w-11 shrink-0 items-center justify-center rounded-full border transition ${
            micActive
              ? "border-hud-orange bg-hud-orange/20 shadow-glowOrange"
              : isSpeaking
                ? "border-hud-cyan bg-hud-cyan/20 shadow-glow"
                : "border-hud-cyan/40 bg-black/30 hover:bg-hud-cyan/10"
          } disabled:opacity-30`}
        >
          <MicIcon active={micActive} />
        </button>

        <div className="w-28 shrink-0">
          <Waveform />
        </div>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder='Type a command… e.g. "open chrome", "weather", "shut down"'
          className="no-drag flex-1 rounded border border-hud-cyan/25 bg-black/40 px-3 py-2 font-mono text-[12.5px] text-hud-white outline-none placeholder:text-hud-white/30 focus:border-hud-cyan/70"
        />

        <button onClick={submit} className="no-drag rounded border border-hud-cyan/40 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-hud-cyan hover:bg-hud-cyan/10">
          Send
        </button>

        <div className="mx-1 h-8 w-px bg-hud-cyan/15" />

        <ToggleChip
          label="Wake Word"
          active={!!settings?.wakeWordEnabled}
          onClick={() => updateSettings({ wakeWordEnabled: !settings?.wakeWordEnabled })}
        />
        <ToggleChip
          label="Animations"
          active={!!settings?.animationsEnabled}
          onClick={() => updateSettings({ animationsEnabled: !settings?.animationsEnabled })}
        />
        <ToggleChip
          label={settings?.theme === "darker" ? "Darker" : "Dark"}
          active={settings?.theme === "darker"}
          onClick={() => updateSettings({ theme: settings?.theme === "darker" ? "dark" : "darker" })}
        />

        <button onClick={onOpenSettings} className="no-drag rounded border border-hud-cyan/30 px-2.5 py-2 text-hud-cyan hover:bg-hud-cyan/10" title="Settings">
          <GearIcon />
        </button>
      </div>
    </HudPanel>
  );
}

function ToggleChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`no-drag whitespace-nowrap rounded border px-2.5 py-2 font-mono text-[9px] uppercase tracking-widest transition ${
        active ? "border-hud-cyan bg-hud-cyan/15 text-hud-cyan text-glow" : "border-white/10 text-hud-white/40 hover:text-hud-white/70"
      }`}
    >
      {label}
    </button>
  );
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className={active ? "text-hud-orange" : "text-hud-cyan"}>
      <path d="M12 15a3 3 0 003-3V6a3 3 0 10-6 0v6a3 3 0 003 3z" stroke="currentColor" strokeWidth="1.6" />
      <path d="M19 11a7 7 0 01-14 0M12 18v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM19.4 12.9l1.6.9-1 1.8-1.8-.6a5.9 5.9 0 01-1.3.8l-.3 1.9h-2l-.3-1.9a5.9 5.9 0 01-1.3-.8l-1.8.6-1-1.8 1.6-.9a6 6 0 010-1.8l-1.6-.9 1-1.8 1.8.6c.4-.3.8-.6 1.3-.8l.3-1.9h2l.3 1.9c.5.2.9.5 1.3.8l1.8-.6 1 1.8-1.6.9a6 6 0 010 1.8z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}
