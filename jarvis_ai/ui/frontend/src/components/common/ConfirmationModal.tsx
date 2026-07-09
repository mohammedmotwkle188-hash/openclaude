import { AnimatePresence, motion } from "framer-motion";
import { useJarvisStore } from "../../state/store";
import { cancelPendingCommand, confirmPendingCommand } from "../../lib/commands/dispatch";

export function ConfirmationModal() {
  const cmd = useJarvisStore((s) => s.pendingConfirmation);

  return (
    <AnimatePresence>
      {cmd && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="hud-panel w-[420px] rounded-lg border-hud-orange/50 p-5"
            style={{ boxShadow: "0 0 40px rgba(255,138,61,0.25)" }}
          >
            <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-hud-orange text-glow-orange">
              <WarnIcon /> Confirmation Required
            </div>
            <p className="mb-4 text-[13.5px] text-hud-white">
              This action is irreversible: <strong>{cmd.label}</strong>. Shall I proceed?
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={cancelPendingCommand}
                className="rounded border border-white/15 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide text-hud-white/60 hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                onClick={() => confirmPendingCommand()}
                className="rounded border border-hud-orange px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide text-hud-orange hover:bg-hud-orange/15"
              >
                Confirm
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function WarnIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M12 3l10 18H2L12 3z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M12 10v4M12 17.5v.01" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
