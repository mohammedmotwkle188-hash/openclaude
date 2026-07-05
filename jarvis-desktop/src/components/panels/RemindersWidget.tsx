import { useEffect, useState } from "react";
import type { ReminderItem } from "../../../shared/types";

export function RemindersWidget() {
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [text, setText] = useState("");

  const refresh = () => window.jarvis.data.remindersList().then(setReminders);
  useEffect(() => {
    refresh();
  }, []);

  const add = async () => {
    if (!text.trim()) return;
    await window.jarvis.data.remindersAdd(text.trim(), Date.now() + 60 * 60 * 1000);
    setText("");
    refresh();
  };

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex gap-1.5">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="New reminder…"
          className="no-drag flex-1 rounded border border-hud-cyan/25 bg-black/30 px-2 py-1 text-[11px] text-hud-white outline-none focus:border-hud-cyan/60"
        />
        <button onClick={add} className="no-drag rounded border border-hud-cyan/40 px-2 text-[11px] text-hud-cyan hover:bg-hud-cyan/10">
          Add
        </button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto">
        {reminders.length === 0 && <div className="font-mono text-[11px] text-hud-white/40">No reminders.</div>}
        {reminders.map((r) => (
          <label key={r.id} className="flex items-center gap-2 text-[11.5px] text-hud-white/80">
            <input
              type="checkbox"
              checked={r.done}
              onChange={async () => {
                await window.jarvis.data.remindersToggle(r.id);
                refresh();
              }}
              className="no-drag accent-cyan-400"
            />
            <span className={r.done ? "line-through opacity-40" : ""}>{r.text}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
