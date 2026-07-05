import { useState } from "react";
import { HudPanel } from "../common/HudPanel";
import { ChatHistory } from "../chat/ChatHistory";
import { ThoughtsFeed } from "./ThoughtsFeed";
import { NotificationsFeed } from "./NotificationsFeed";
import { WeatherWidget } from "./WeatherWidget";
import { NewsFeed } from "./NewsFeed";
import { RemindersWidget } from "./RemindersWidget";
import { CalendarWidget } from "./CalendarWidget";
import { useJarvisStore } from "../../state/store";

const TABS = ["Chat", "Thoughts", "Alerts", "Schedule"] as const;
type Tab = (typeof TABS)[number];

export function RightPanel() {
  const [tab, setTab] = useState<Tab>("Chat");
  const transcript = useJarvisStore((s) => s.transcript);
  const isListening = useJarvisStore((s) => s.isListening);

  return (
    <div className="flex h-full w-full flex-col gap-3">
      <HudPanel className="flex-1 overflow-hidden" title="Jarvis Interface" right={
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`no-drag rounded px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest transition ${
                tab === t ? "bg-hud-cyan/20 text-hud-cyan" : "text-hud-white/40 hover:text-hud-white/70"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      }>
        <div className="flex h-full flex-col">
          <div className="min-h-0 flex-1 overflow-hidden" style={{ maxHeight: "calc(100% - 1.5rem)" }}>
            {tab === "Chat" && <ChatHistory />}
            {tab === "Thoughts" && <ThoughtsFeed />}
            {tab === "Alerts" && <NotificationsFeed />}
            {tab === "Schedule" && (
              <div className="flex h-full flex-col gap-3 overflow-y-auto">
                <div>
                  <div className="mb-1 font-mono text-[9px] uppercase tracking-widest text-hud-cyan/60">Calendar</div>
                  <CalendarWidget />
                </div>
                <div className="flex-1">
                  <div className="mb-1 font-mono text-[9px] uppercase tracking-widest text-hud-cyan/60">Reminders</div>
                  <RemindersWidget />
                </div>
              </div>
            )}
          </div>
          {tab === "Chat" && isListening && transcript && (
            <div className="mt-2 border-t border-hud-cyan/15 pt-2 font-mono text-[11px] italic text-hud-cyan/70">
              "{transcript}"
            </div>
          )}
        </div>
      </HudPanel>

      <HudPanel title="Weather">
        <WeatherWidget />
      </HudPanel>

      <HudPanel title="News" className="max-h-40 overflow-hidden">
        <NewsFeed />
      </HudPanel>
    </div>
  );
}
