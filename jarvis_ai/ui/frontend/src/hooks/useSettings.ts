import { useCallback, useEffect } from "react";
import { useJarvisStore } from "../state/store";
import type { AppSettings } from "../../shared/types";

export function useSettings() {
  const settings = useJarvisStore((s) => s.settings);
  const setSettingsState = useJarvisStore((s) => s.setSettings);

  useEffect(() => {
    window.jarvis.settings.get().then(setSettingsState);
  }, [setSettingsState]);

  const updateSettings = useCallback(
    async (partial: Partial<AppSettings>) => {
      const next = await window.jarvis.settings.set(partial);
      setSettingsState(next);
    },
    [setSettingsState],
  );

  return { settings, updateSettings };
}
