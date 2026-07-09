import type { JarvisBridge } from "../lib/bridge";

declare global {
  interface Window {
    jarvis: JarvisBridge;
    pywebview?: { api: Record<string, (...args: any[]) => Promise<any>> };
  }
}

export {};
