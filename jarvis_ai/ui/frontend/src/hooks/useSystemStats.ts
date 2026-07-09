import { useEffect } from "react";
import { useJarvisStore } from "../state/store";

export function useSystemStats() {
  const setStats = useJarvisStore((s) => s.setStats);
  const setOnline = useJarvisStore((s) => s.setOnline);

  useEffect(() => {
    const offUpdate = window.jarvis.stats.onUpdate(setStats);
    const offNet = window.jarvis.stats.onInternetStatus(setOnline);
    window.jarvis.stats.subscribe();
    return () => {
      offUpdate();
      offNet();
    };
  }, [setStats, setOnline]);
}
