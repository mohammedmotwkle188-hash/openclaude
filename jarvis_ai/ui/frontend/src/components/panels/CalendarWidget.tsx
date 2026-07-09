import { useEffect, useState } from "react";
import type { CalendarEventItem } from "../../../shared/types";

export function CalendarWidget() {
  const [events, setEvents] = useState<CalendarEventItem[]>([]);

  useEffect(() => {
    window.jarvis.data.calendarList().then(setEvents);
  }, []);

  return (
    <div className="flex flex-col gap-1.5">
      {events.length === 0 && (
        <div className="font-mono text-[11px] text-hud-white/40">
          No events. Connect a calendar provider in Settings to sync your schedule.
        </div>
      )}
      {events.map((e) => (
        <div key={e.id} className="rounded border border-hud-cyan/20 bg-hud-cyan/5 px-2 py-1 text-[11.5px] text-hud-white/80">
          <div className="font-medium">{e.title}</div>
          <div className="font-mono text-[10px] text-hud-cyan/60">
            {new Date(e.startAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} –{" "}
            {new Date(e.endAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
      ))}
    </div>
  );
}
