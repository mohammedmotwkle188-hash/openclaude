import type { PropsWithChildren, ReactNode } from "react";

interface HudPanelProps {
  title?: string;
  className?: string;
  right?: ReactNode;
}

export function HudPanel({ title, className = "", right, children }: PropsWithChildren<HudPanelProps>) {
  return (
    <div className={`hud-panel rounded-md p-3 ${className}`}>
      <div className="hud-corner tl" />
      <div className="hud-corner tr" />
      <div className="hud-corner bl" />
      <div className="hud-corner br" />
      {title && (
        <div className="mb-2 flex items-center justify-between border-b border-hud-cyan/15 pb-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-hud-cyan/80">{title}</span>
          {right}
        </div>
      )}
      <div className="relative">{children}</div>
    </div>
  );
}
