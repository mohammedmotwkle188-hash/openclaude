import { randomUUID } from "node:crypto";
import type { ParsedCommand } from "../../../shared/types";

interface Rule {
  test: RegExp;
  action: string;
  risk: "safe" | "confirm";
  label: (m: RegExpMatchArray) => string;
  args: (m: RegExpMatchArray) => Record<string, string>;
}

const rules: Rule[] = [
  { test: /^open (chrome|spotify|discord|vscode|vs code|steam|netflix|youtube|camera)$/i, action: "open_app", risk: "safe",
    label: (m) => `Open ${m[1]}`, args: (m) => ({ app: m[1].replace("vs code", "vscode") }) },
  { test: /^(?:play|resume) music$/i, action: "media_play", risk: "safe", label: () => "Play music", args: () => ({}) },
  { test: /^(?:stop) music$/i, action: "media_stop", risk: "safe", label: () => "Stop music", args: () => ({}) },
  { test: /^pause music$/i, action: "media_pause", risk: "safe", label: () => "Pause music", args: () => ({}) },
  { test: /^next (?:track|song)$/i, action: "media_next", risk: "safe", label: () => "Next track", args: () => ({}) },
  { test: /^(?:previous|prev|last) (?:track|song)$/i, action: "media_prev", risk: "safe", label: () => "Previous track", args: () => ({}) },
  { test: /^shut ?down(?: the)?(?: pc| computer)?$/i, action: "shutdown_pc", risk: "confirm", label: () => "Shut down this computer", args: () => ({}) },
  { test: /^restart(?: the)?(?: pc| computer)?$/i, action: "restart_pc", risk: "confirm", label: () => "Restart this computer", args: () => ({}) },
  { test: /^search google for (.+)$/i, action: "search_google", risk: "safe", label: (m) => `Search Google: ${m[1]}`, args: (m) => ({ query: m[1] }) },
  { test: /^search youtube for (.+)$/i, action: "search_youtube", risk: "safe", label: (m) => `Search YouTube: ${m[1]}`, args: (m) => ({ query: m[1] }) },
  { test: /^set volume to (\d{1,3})%?$/i, action: "set_volume", risk: "safe", label: (m) => `Set volume to ${m[1]}%`, args: (m) => ({ percent: m[1] }) },
  { test: /^set brightness to (\d{1,3})%?$/i, action: "set_brightness", risk: "safe", label: (m) => `Set brightness to ${m[1]}%`, args: (m) => ({ percent: m[1] }) },
  { test: /^take (?:a )?screenshot$/i, action: "screenshot", risk: "safe", label: () => "Take a screenshot", args: () => ({}) },
  { test: /^open camera$/i, action: "open_app", risk: "safe", label: () => "Open camera", args: () => ({ app: "camera" }) },
  { test: /^open folder (.+)$/i, action: "open_folder", risk: "safe", label: (m) => `Open folder ${m[1]}`, args: (m) => ({ path: m[1] }) },
  { test: /^create file (\S+)$/i, action: "create_file", risk: "safe", label: (m) => `Create file ${m[1]}`, args: (m) => ({ path: m[1] }) },
  { test: /^delete file (\S+)$/i, action: "delete_file", risk: "confirm", label: (m) => `Delete file ${m[1]}`, args: (m) => ({ path: m[1] }) },
  { test: /^move (\S+) to (\S+)$/i, action: "move_file", risk: "confirm", label: (m) => `Move ${m[1]} to ${m[2]}`, args: (m) => ({ from: m[1], to: m[2] }) },
  { test: /^rename (\S+) to (\S+)$/i, action: "rename_file", risk: "safe", label: (m) => `Rename ${m[1]} to ${m[2]}`, args: (m) => ({ path: m[1], name: m[2] }) },
  { test: /^weather(?: in (.+))?$/i, action: "weather", risk: "safe", label: (m) => `Weather${m[1] ? ` in ${m[1]}` : ""}`, args: (m) => ({ location: m[1] ?? "" }) },
  { test: /^news$/i, action: "news", risk: "safe", label: () => "Latest headlines", args: () => ({}) },
  { test: /^stock(?:s)? (?:price )?(?:for |of )?([A-Za-z.]{1,6})$/i, action: "stock", risk: "safe", label: (m) => `Stock price: ${m[1].toUpperCase()}`, args: (m) => ({ symbol: m[1] }) },
  { test: /^crypto(?: price)? (?:for |of )?(\w{2,10})$/i, action: "crypto", risk: "safe", label: (m) => `Crypto price: ${m[1].toUpperCase()}`, args: (m) => ({ symbol: m[1] }) },
];

export function parseCommand(raw: string): ParsedCommand | null {
  const text = raw.trim();
  for (const rule of rules) {
    const m = text.match(rule.test);
    if (m) {
      return { id: randomUUID(), raw: text, action: rule.action, args: rule.args(m), risk: rule.risk, label: rule.label(m) };
    }
  }
  return null;
}
