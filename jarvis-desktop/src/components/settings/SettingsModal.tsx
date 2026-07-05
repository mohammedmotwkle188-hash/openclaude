import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useSettings } from "../../hooks/useSettings";
import { listBritishVoices } from "../../lib/voice/tts";
import type { AiProviderId, ApiKeySet } from "../../../shared/types";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

const PROVIDER_LABELS: Record<AiProviderId, string> = {
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  gemini: "Google Gemini",
  ollama: "Ollama (local)",
};

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  const { settings, updateSettings } = useSettings();
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [apiKeys, setApiKeys] = useState<Partial<ApiKeySet>>({});
  const [maskedKeys, setMaskedKeys] = useState<Record<string, boolean>>({});
  const [passphrase, setPassphrase] = useState("");
  const [vaultMsg, setVaultMsg] = useState("");

  useEffect(() => {
    if (!open) return;
    const load = () => setVoices(listBritishVoices());
    load();
    window.speechSynthesis.onvoiceschanged = load;
    window.jarvis.settings.getMaskedApiKeys().then(setMaskedKeys);
  }, [open]);

  if (!settings) return null;

  const saveKeys = async () => {
    await window.jarvis.settings.setApiKeys(apiKeys);
    setApiKeys({});
    window.jarvis.settings.getMaskedApiKeys().then(setMaskedKeys);
  };

  const setPass = async () => {
    if (!passphrase.trim()) return;
    await window.jarvis.memory.setPassphrase(passphrase);
    setVaultMsg("Vault unlocked and passphrase set. New memories will be encrypted at rest.");
    setPassphrase("");
  };

  const moveProvider = (id: AiProviderId, dir: -1 | 1) => {
    const order = [...settings.providerOrder];
    const idx = order.indexOf(id);
    const swapWith = idx + dir;
    if (swapWith < 0 || swapWith >= order.length) return;
    [order[idx], order[swapWith]] = [order[swapWith], order[idx]];
    updateSettings({ providerOrder: order });
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            onClick={(e) => e.stopPropagation()}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="hud-panel max-h-[85vh] w-[560px] overflow-y-auto rounded-lg p-6"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-hud text-lg tracking-widest text-hud-white text-glow">SETTINGS</h2>
              <button onClick={onClose} className="text-hud-white/50 hover:text-hud-white">✕</button>
            </div>

            <Section title="Voice">
              <Row label="Voice enabled">
                <Switch checked={settings.voiceEnabled} onChange={(v) => updateSettings({ voiceEnabled: v })} />
              </Row>
              <Row label="Wake word ('Jarvis')">
                <Switch checked={settings.wakeWordEnabled} onChange={(v) => updateSettings({ wakeWordEnabled: v })} />
              </Row>
              <Row label="British voice">
                <select
                  value={settings.voiceName ?? ""}
                  onChange={(e) => updateSettings({ voiceName: e.target.value || null })}
                  className="no-drag rounded border border-hud-cyan/30 bg-black/40 px-2 py-1 text-[12px] text-hud-white"
                >
                  <option value="">Auto (best available)</option>
                  {voices.map((v) => (
                    <option key={v.name} value={v.name}>{v.name}</option>
                  ))}
                </select>
              </Row>
              {voices.length === 0 && (
                <p className="font-mono text-[10px] text-hud-white/40">
                  No en-GB voices found on this system. Speech will fall back to the closest available voice — install
                  an English (UK) voice pack in your OS for authentic British pronunciation.
                </p>
              )}
              <Row label={`Speech rate (${settings.speechRate.toFixed(2)}x)`}>
                <input
                  type="range"
                  min="0.75"
                  max="1.5"
                  step="0.05"
                  value={settings.speechRate}
                  onChange={(e) => updateSettings({ speechRate: Number(e.target.value) })}
                  className="no-drag w-32"
                />
              </Row>
            </Section>

            <Section title="Appearance">
              <Row label="Theme">
                <Switch checked={settings.theme === "darker"} onChange={(v) => updateSettings({ theme: v ? "darker" : "dark" })} onLabel="Darker" offLabel="Dark" />
              </Row>
              <Row label="Animations">
                <Switch checked={settings.animationsEnabled} onChange={(v) => updateSettings({ animationsEnabled: v })} />
              </Row>
            </Section>

            <Section title="AI Model Fallback Order">
              <div className="space-y-1.5">
                {settings.providerOrder.map((id, i) => (
                  <div key={id} className="flex items-center justify-between rounded border border-hud-cyan/15 px-2 py-1 text-[12px] text-hud-white/80">
                    <span>{i + 1}. {PROVIDER_LABELS[id]}</span>
                    <div className="flex gap-1">
                      <button onClick={() => moveProvider(id, -1)} className="no-drag px-1.5 text-hud-cyan/70 hover:text-hud-cyan">↑</button>
                      <button onClick={() => moveProvider(id, 1)} className="no-drag px-1.5 text-hud-cyan/70 hover:text-hud-cyan">↓</button>
                    </div>
                  </div>
                ))}
              </div>
              <Row label="Ollama base URL">
                <input
                  value={settings.ollamaBaseUrl}
                  onChange={(e) => updateSettings({ ollamaBaseUrl: e.target.value })}
                  className="no-drag rounded border border-hud-cyan/30 bg-black/40 px-2 py-1 text-[12px] text-hud-white"
                />
              </Row>
            </Section>

            <Section title="API Keys">
              {(["anthropic", "openai", "gemini", "openweather", "newsapi"] as const).map((k) => (
                <Row key={k} label={`${k}${maskedKeys[k] ? " ✓ configured" : ""}`}>
                  <input
                    type="password"
                    placeholder={maskedKeys[k] ? "•••••••• (set)" : "Enter key"}
                    value={apiKeys[k] ?? ""}
                    onChange={(e) => setApiKeys((prev) => ({ ...prev, [k]: e.target.value }))}
                    className="no-drag w-48 rounded border border-hud-cyan/30 bg-black/40 px-2 py-1 text-[12px] text-hud-white"
                  />
                </Row>
              ))}
              <button onClick={saveKeys} className="no-drag mt-1 rounded border border-hud-cyan/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide text-hud-cyan hover:bg-hud-cyan/10">
                Save Keys
              </button>
            </Section>

            <Section title="Security & Memory">
              <p className="mb-2 font-mono text-[10.5px] leading-relaxed text-hud-white/50">
                Set a local passphrase to encrypt chat history and remembered facts at rest (AES-256-GCM). Losing the
                passphrase means losing access to encrypted memories — there is no recovery path by design.
              </p>
              <div className="flex gap-1.5">
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="Vault passphrase"
                  className="no-drag flex-1 rounded border border-hud-cyan/30 bg-black/40 px-2 py-1 text-[12px] text-hud-white"
                />
                <button onClick={setPass} className="no-drag rounded border border-hud-cyan/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide text-hud-cyan hover:bg-hud-cyan/10">
                  Set / Unlock
                </button>
              </div>
              {vaultMsg && <p className="mt-1.5 font-mono text-[10.5px] text-hud-cyan/70">{vaultMsg}</p>}
              <p className="mt-3 font-mono text-[10px] leading-relaxed text-hud-white/35">
                Password-manager (1Password/Bitwarden) integration and cloud sync are architected as pluggable
                extension points but are not wired to a live third-party account in this build — see README.
              </p>
            </Section>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.25em] text-hud-cyan/70">{title}</div>
      <div className="space-y-2 border-l border-hud-cyan/10 pl-3">{children}</div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[12px] text-hud-white/70">{label}</span>
      {children}
    </div>
  );
}

function Switch({
  checked,
  onChange,
  onLabel = "On",
  offLabel = "Off",
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  onLabel?: string;
  offLabel?: string;
}) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`no-drag rounded border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition ${
        checked ? "border-hud-cyan bg-hud-cyan/15 text-hud-cyan" : "border-white/15 text-hud-white/40"
      }`}
    >
      {checked ? onLabel : offLabel}
    </button>
  );
}
