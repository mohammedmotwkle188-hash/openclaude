import type { JarvisApi } from "../../electron/preload";

declare global {
  interface Window {
    jarvis: JarvisApi;
  }
}

export {};
