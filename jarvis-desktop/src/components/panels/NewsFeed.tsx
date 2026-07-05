import { useEffect, useState } from "react";
import type { NewsHeadline } from "../../../shared/types";

export function NewsFeed() {
  const [headlines, setHeadlines] = useState<NewsHeadline[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    window.jarvis.data
      .news()
      .then((n: NewsHeadline[]) => !cancelled && setHeadlines(n))
      .catch((err) => !cancelled && setError(err?.message ?? "News unavailable"));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="font-mono text-[11px] text-hud-white/40">{error}</div>;

  return (
    <div className="flex flex-col gap-1.5 overflow-y-auto">
      {headlines.length === 0 && <div className="font-mono text-[11px] text-hud-white/40">Loading headlines…</div>}
      {headlines.map((h) => (
        <a key={h.id} href={h.url} target="_blank" rel="noreferrer" className="block text-[11.5px] text-hud-white/80 hover:text-hud-cyan">
          {h.title}
          <span className="ml-1 font-mono text-[9px] text-hud-cyan/50">{h.source}</span>
        </a>
      ))}
    </div>
  );
}
