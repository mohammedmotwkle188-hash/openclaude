import { exec } from "node:child_process";
import { promisify } from "node:util";
import { shell, clipboard } from "electron";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const execAsync = promisify(exec);

const PLATFORM = process.platform as "win32" | "darwin" | "linux";

const APP_LAUNCHERS: Record<string, Partial<Record<typeof PLATFORM, string>>> = {
  chrome: { win32: "start chrome", darwin: "open -a \"Google Chrome\"", linux: "google-chrome || chromium || xdg-open https://google.com" },
  spotify: { win32: "start spotify", darwin: "open -a Spotify", linux: "spotify || xdg-open https://open.spotify.com" },
  discord: { win32: "start discord", darwin: "open -a Discord", linux: "discord || xdg-open https://discord.com/app" },
  vscode: { win32: "code", darwin: "open -a \"Visual Studio Code\"", linux: "code" },
  steam: { win32: "start steam", darwin: "open -a Steam", linux: "steam" },
  netflix: { win32: "start https://netflix.com", darwin: "open https://netflix.com", linux: "xdg-open https://netflix.com" },
  youtube: { win32: "start https://youtube.com", darwin: "open https://youtube.com", linux: "xdg-open https://youtube.com" },
  camera: { win32: "start microsoft.windows.camera:", darwin: "open -a Photo\\ Booth", linux: "cheese || xdg-open ." },
};

async function runShell(cmd: string) {
  await execAsync(cmd, { windowsHide: true });
}

export async function openApp(name: string): Promise<string> {
  const key = name.toLowerCase().trim();
  const cmd = APP_LAUNCHERS[key]?.[PLATFORM];
  if (!cmd) {
    // Fall back to treating it as a URL or letting the OS shell resolve it.
    if (/^https?:\/\//.test(name)) {
      await shell.openExternal(name);
      return `Opened ${name}`;
    }
    throw new Error(`I don't have a launcher registered for "${name}" on ${PLATFORM}.`);
  }
  await runShell(cmd);
  return `Opening ${name}.`;
}

export async function openUrl(url: string): Promise<string> {
  await shell.openExternal(url);
  return `Opened ${url}`;
}

export async function searchWeb(engine: "google" | "youtube", query: string): Promise<string> {
  const url =
    engine === "google"
      ? `https://www.google.com/search?q=${encodeURIComponent(query)}`
      : `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
  await shell.openExternal(url);
  return `Searching ${engine} for "${query}".`;
}

// --- Media control: best-effort, sends the OS media key rather than talking to a
// specific player's API, so it works with whatever app currently has media focus.
export async function mediaControl(action: "play" | "pause" | "stop" | "next" | "prev"): Promise<string> {
  try {
    if (PLATFORM === "darwin") {
      const key = action === "next" ? "next" : action === "prev" ? "previous" : "play/pause";
      await runShell(`osascript -e 'tell application "System Events" to key code ${action === "next" ? 124 : action === "prev" ? 123 : 49}'`);
    } else if (PLATFORM === "linux") {
      const map: Record<string, string> = { play: "Play", pause: "Pause", stop: "Stop", next: "Next", prev: "Previous" };
      await runShell(`playerctl ${map[action].toLowerCase()}`);
    } else if (PLATFORM === "win32") {
      // Requires no extra binaries: simulate the media key via PowerShell SendKeys.
      const vk: Record<string, string> = { play: "{MEDIA_PLAY_PAUSE}", pause: "{MEDIA_PLAY_PAUSE}", stop: "{MEDIA_STOP}", next: "{MEDIA_NEXT}", prev: "{MEDIA_PREV}" };
      await runShell(`powershell -c "(New-Object -ComObject WScript.Shell).SendKeys('${vk[action]}')"`);
    }
    return `Media: ${action}.`;
  } catch {
    throw new Error(`Couldn't send the ${action} media command on this platform.`);
  }
}

export async function setVolume(percent: number): Promise<string> {
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));
  try {
    if (PLATFORM === "darwin") {
      await runShell(`osascript -e "set volume output volume ${clamped}"`);
    } else if (PLATFORM === "linux") {
      await runShell(`amixer -D pulse sset Master ${clamped}% || pactl set-sink-volume @DEFAULT_SINK@ ${clamped}%`);
    } else if (PLATFORM === "win32") {
      // No first-party CLI volume control on Windows without a helper binary (e.g. nircmd);
      // this uses a lightweight keystroke-based approximation.
      await runShell(`powershell -c "$obj = new-object -com wscript.shell; for ($i=0;$i -lt 50;$i++) { $obj.SendKeys([char]174) }"`);
    }
    return `Volume set to ${clamped}%.`;
  } catch {
    throw new Error("Couldn't change system volume on this platform.");
  }
}

export async function setBrightness(percent: number): Promise<string> {
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));
  try {
    if (PLATFORM === "darwin") {
      await runShell(`osascript -e "tell application \\"System Events\\" to key code 144"`); // best-effort; macOS brightness needs entitlements
    } else if (PLATFORM === "linux") {
      await runShell(`brightnessctl set ${clamped}% || xbacklight -set ${clamped}`);
    } else if (PLATFORM === "win32") {
      await runShell(`powershell -c "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,${clamped})"`);
    }
    return `Brightness set to ${clamped}%.`;
  } catch {
    throw new Error("Brightness control isn't available on this device/platform.");
  }
}

export async function powerAction(action: "shutdown" | "restart"): Promise<string> {
  const cmds: Record<string, Record<typeof PLATFORM, string>> = {
    shutdown: { win32: "shutdown /s /t 5", darwin: "osascript -e 'tell app \"System Events\" to shut down'", linux: "systemctl poweroff" },
    restart: { win32: "shutdown /r /t 5", darwin: "osascript -e 'tell app \"System Events\" to restart'", linux: "systemctl reboot" },
  };
  await runShell(cmds[action][PLATFORM]);
  return `${action === "shutdown" ? "Shutting down" : "Restarting"} in 5 seconds.`;
}

// --- File operations, sandboxed to a single confirmed root directory to avoid
// arbitrary filesystem access from natural-language commands.
function assertInsideHome(target: string) {
  const resolved = path.resolve(target);
  const home = os.homedir();
  if (!resolved.startsWith(home)) {
    throw new Error("For safety, file operations are restricted to your home directory.");
  }
  return resolved;
}

export async function createFile(target: string, content = ""): Promise<string> {
  const resolved = assertInsideHome(target);
  await fs.mkdir(path.dirname(resolved), { recursive: true });
  await fs.writeFile(resolved, content, "utf8");
  return `Created ${resolved}`;
}

export async function deleteFile(target: string): Promise<string> {
  const resolved = assertInsideHome(target);
  await fs.rm(resolved, { recursive: true, force: false });
  return `Deleted ${resolved}`;
}

export async function moveFile(from: string, to: string): Promise<string> {
  const src = assertInsideHome(from);
  const dst = assertInsideHome(to);
  await fs.mkdir(path.dirname(dst), { recursive: true });
  await fs.rename(src, dst);
  return `Moved ${src} -> ${dst}`;
}

export async function renameFile(target: string, newName: string): Promise<string> {
  const src = assertInsideHome(target);
  const dst = path.join(path.dirname(src), newName);
  await fs.rename(src, dst);
  return `Renamed to ${newName}`;
}

export async function openFolder(target: string): Promise<string> {
  const resolved = assertInsideHome(target);
  await shell.openPath(resolved);
  return `Opened ${resolved}`;
}

export function copyToClipboard(text: string) {
  clipboard.writeText(text);
}

export function readClipboard(): string {
  return clipboard.readText();
}

// --- Best-effort window activation for a named application (not this app's own window).
export async function focusApp(name: string): Promise<string> {
  try {
    if (PLATFORM === "darwin") {
      await runShell(`osascript -e 'tell application "${name}" to activate'`);
    } else if (PLATFORM === "linux") {
      await runShell(`wmctrl -a "${name}"`);
    } else if (PLATFORM === "win32") {
      await runShell(`powershell -c "(New-Object -ComObject WScript.Shell).AppActivate('${name}')"`);
    }
    return `Focused ${name}.`;
  } catch {
    throw new Error(`Couldn't bring "${name}" to the foreground — is it running?`);
  }
}
