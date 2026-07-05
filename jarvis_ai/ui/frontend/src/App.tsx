import { useState } from "react";
import { TopBar } from "./components/hud/TopBar";
import { Radar } from "./components/hud/Radar";
import { LeftPanel } from "./components/panels/LeftPanel";
import { RightPanel } from "./components/panels/RightPanel";
import { BottomPanel } from "./components/panels/BottomPanel";
import { SettingsModal } from "./components/settings/SettingsModal";
import { ConfirmationModal } from "./components/common/ConfirmationModal";
import { useSystemStats } from "./hooks/useSystemStats";
import { useSettings } from "./hooks/useSettings";
import { useBridgeEvents } from "./hooks/useBridgeEvents";

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { settings } = useSettings();
  useSystemStats();
  useBridgeEvents();

  const animationsEnabled = settings?.animationsEnabled ?? true;
  const darker = settings?.theme === "darker";

  return (
    <div className={`relative flex h-screen w-screen flex-col gap-3 overflow-hidden bg-grid p-3 ${darker ? "brightness-[0.85]" : ""}`}>
      <div className="vignette pointer-events-none absolute inset-0" style={{ boxShadow: "inset 0 0 220px rgba(0,0,0,0.85)" }} />

      <TopBar />

      <div className="relative grid min-h-0 flex-1 grid-cols-[300px_1fr_340px] gap-3">
        <LeftPanel />

        <div className="relative flex items-center justify-center overflow-hidden">
          <Radar animationsEnabled={animationsEnabled} />
        </div>

        <RightPanel />
      </div>

      <BottomPanel onOpenSettings={() => setSettingsOpen(true)} />

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ConfirmationModal />
    </div>
  );
}
