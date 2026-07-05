import { mouse, keyboard, screen, Button, Key, straightTo } from "@nut-tree-fork/nut-js";

// Real cursor/keyboard control. This is intentionally low-level: primitives Jarvis can
// compose (move, click, type, press, scroll) rather than an autonomous "do this task"
// planner. Requires OS-level accessibility/input permissions once packaged — see README.

keyboard.config.autoDelayMs = 15;
mouse.config.autoDelayMs = 8;

const MODIFIER_KEYS: Record<string, Key> = {
  ctrl: Key.LeftControl,
  control: Key.LeftControl,
  cmd: Key.LeftCmd,
  command: Key.LeftCmd,
  super: Key.LeftSuper,
  win: Key.LeftSuper,
  alt: Key.LeftAlt,
  option: Key.LeftAlt,
  shift: Key.LeftShift,
};

const NAMED_KEYS: Record<string, Key> = {
  enter: Key.Enter,
  return: Key.Enter,
  escape: Key.Escape,
  esc: Key.Escape,
  tab: Key.Tab,
  space: Key.Space,
  backspace: Key.Backspace,
  delete: Key.Delete,
  up: Key.Up,
  down: Key.Down,
  left: Key.Left,
  right: Key.Right,
  home: Key.Home,
  end: Key.End,
  pageup: Key.PageUp,
  pagedown: Key.PageDown,
};

/** Cross-platform modifier for copy/paste/select-all/undo — Cmd on macOS, Ctrl elsewhere. */
function primaryModifier(): Key {
  return process.platform === "darwin" ? Key.LeftCmd : Key.LeftControl;
}

export async function getScreenSize(): Promise<{ width: number; height: number }> {
  return { width: await screen.width(), height: await screen.height() };
}

/** Moves the cursor to a point given as fractions (0.0-1.0) of the primary screen. */
export async function moveToFraction(xFrac: number, yFrac: number): Promise<{ x: number; y: number }> {
  const { width, height } = await getScreenSize();
  const x = Math.round(Math.max(0, Math.min(1, xFrac)) * width);
  const y = Math.round(Math.max(0, Math.min(1, yFrac)) * height);
  await mouse.move(straightTo({ x, y }));
  return { x, y };
}

export async function clickAt(xFrac?: number, yFrac?: number, button: "left" | "right" | "middle" = "left"): Promise<string> {
  if (xFrac != null && yFrac != null) await moveToFraction(xFrac, yFrac);
  const btn = button === "right" ? Button.RIGHT : button === "middle" ? Button.MIDDLE : Button.LEFT;
  await mouse.click(btn);
  return `Clicked (${button}).`;
}

export async function doubleClickAt(xFrac?: number, yFrac?: number): Promise<string> {
  if (xFrac != null && yFrac != null) await moveToFraction(xFrac, yFrac);
  await mouse.doubleClick(Button.LEFT);
  return "Double-clicked.";
}

export async function scroll(direction: "up" | "down" | "left" | "right", amount = 5): Promise<string> {
  if (direction === "up") await mouse.scrollUp(amount);
  else if (direction === "down") await mouse.scrollDown(amount);
  else if (direction === "left") await mouse.scrollLeft(amount);
  else await mouse.scrollRight(amount);
  return `Scrolled ${direction}.`;
}

export async function typeText(text: string): Promise<string> {
  await keyboard.type(text);
  return `Typed "${text}".`;
}

/** Parses "ctrl+shift+t" style combos, or a single named/plain-character key. */
export async function pressKeyCombo(combo: string): Promise<string> {
  const parts = combo
    .toLowerCase()
    .split(/[\s+]+/)
    .filter(Boolean);

  const keys: Key[] = parts.map((part) => {
    if (MODIFIER_KEYS[part]) return MODIFIER_KEYS[part];
    if (NAMED_KEYS[part]) return NAMED_KEYS[part];
    if (part.length === 1 && /[a-z0-9]/i.test(part)) {
      const upper = part.toUpperCase();
      const key = (Key as unknown as Record<string, Key>)[upper];
      if (key !== undefined) return key;
    }
    throw new Error(`Unrecognized key "${part}" in combo "${combo}".`);
  });

  await keyboard.pressKey(...keys);
  await keyboard.releaseKey(...keys);
  return `Pressed ${combo}.`;
}

export async function hotkey(action: "copy" | "paste" | "cut" | "undo" | "redo" | "selectAll"): Promise<string> {
  const mod = primaryModifier();
  const map: Record<typeof action, Key> = {
    copy: Key.C,
    paste: Key.V,
    cut: Key.X,
    undo: Key.Z,
    redo: Key.Y,
    selectAll: Key.A,
  };
  const key = map[action];
  await keyboard.pressKey(mod, key);
  await keyboard.releaseKey(mod, key);
  return `${action === "selectAll" ? "Selected all" : action[0].toUpperCase() + action.slice(1) + "d"}.`;
}
