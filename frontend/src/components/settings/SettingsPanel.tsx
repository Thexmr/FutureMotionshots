import { useEffect, useState } from "react";
import type { StudioSettings } from "@shared/types";
import { api } from "../../api/client";

type Tab = "providers" | "routing" | "transcription" | "captions" | "output";
const TABS: { id: Tab; label: string }[] = [
  { id: "providers", label: "Provider & Keys" },
  { id: "routing", label: "Modell-Routing" },
  { id: "transcription", label: "Transkription" },
  { id: "captions", label: "Captions" },
  { id: "output", label: "Output" },
];

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [settings, setSettings] = useState<StudioSettings | null>(null);
  const [tab, setTab] = useState<Tab>("providers");
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    void api.getSettings().then(setSettings);
  }, []);

  if (!settings) return null;

  const save = async () => {
    await api.saveSettings(settings);
    onClose();
  };

  const test = async (id: string) => {
    setTesting(id);
    const res = await api.testProvider(id);
    setSettings((s) =>
      s
        ? {
            ...s,
            providers: s.providers.map((p) =>
              p.id === id
                ? { ...p, status: res.status as never, status_detail: res.detail }
                : p,
            ),
          }
        : s,
    );
    setTesting(null);
  };

  const setKey = (id: string, key: string) =>
    setSettings((s) =>
      s
        ? { ...s, providers: s.providers.map((p) => (p.id === id ? { ...p, api_key: key } : p)) }
        : s,
    );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <div className="panel flex h-[80vh] w-full max-w-4xl overflow-hidden">
        <nav className="w-52 border-r border-line p-3">
          <h2 className="mb-3 px-2 text-sm font-medium">Einstellungen</h2>
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`block w-full rounded-control px-3 py-2 text-left text-sm ${
                tab === t.id ? "bg-elev text-ink" : "text-ink-dim hover:text-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            {tab === "providers" && (
              <div className="space-y-3">
                {settings.providers.map((p) => (
                  <div key={p.id} className="ctl p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{p.label}</span>
                      <StatusDot status={p.status} />
                    </div>
                    {p.id !== "ollama" && (
                      <input
                        type="password"
                        placeholder="API-Key"
                        defaultValue={p.api_key ?? ""}
                        onChange={(e) => setKey(p.id, e.target.value)}
                        className="mt-2 w-full rounded bg-base px-3 py-2 text-sm outline-none"
                      />
                    )}
                    <div className="mt-2 flex items-center gap-3">
                      <button
                        onClick={() => test(p.id)}
                        className="text-xs text-accent hover:text-accent-hi"
                      >
                        {testing === p.id ? "teste…" : "Verbindung testen"}
                      </button>
                      {p.status_detail && (
                        <span className="truncate text-xs text-ink-dim">{p.status_detail}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === "routing" && (
              <div className="space-y-2">
                <p className="mb-2 text-sm text-ink-dim">
                  Welches Modell erledigt welche Aufgabe — mit Fallback.
                </p>
                {settings.routing.map((r, i) => (
                  <div key={i} className="ctl flex items-center gap-3 px-3 py-2 text-sm">
                    <span className="w-40 font-mono text-xs text-accent">{r.task}</span>
                    <span>{r.provider}</span>
                    <span className="text-ink-dim">·</span>
                    <span className="font-mono text-xs">{r.model}</span>
                    {r.fallback_provider && (
                      <span className="ml-auto text-xs text-ink-dim">
                        ↳ {r.fallback_provider}/{r.fallback_model}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {tab === "transcription" && (
              <div className="space-y-3 text-sm">
                <label className="block">
                  <span className="text-ink-dim">Whisper-Modell (lokal)</span>
                  <select
                    value={settings.whisper_model}
                    onChange={(e) =>
                      setSettings({ ...settings, whisper_model: e.target.value as never })
                    }
                    className="ctl mt-1 block w-full px-3 py-2"
                  >
                    {["tiny", "base", "small", "medium", "large-v3"].map((m) => (
                      <option key={m}>{m}</option>
                    ))}
                  </select>
                </label>
                <p className="text-xs text-ink-dim">
                  Lokal-first: läuft offline über faster-whisper, ohne Cloud-Key.
                </p>
              </div>
            )}

            {tab === "captions" && (
              <p className="text-sm text-ink-dim">
                10 Caption-Stile (studio, kinetic-pop, karaoke, typewriter, broadcast,
                bold-impact, wave, minimal, neon, documentary) — pro Projekt im
                Caption-Tab wählbar.
              </p>
            )}

            {tab === "output" && (
              <div className="space-y-3 text-sm">
                <label className="block">
                  <span className="text-ink-dim">Hardware-Beschleunigung</span>
                  <select
                    value={settings.hardware_accel}
                    onChange={(e) =>
                      setSettings({ ...settings, hardware_accel: e.target.value as never })
                    }
                    className="ctl mt-1 block w-full px-3 py-2"
                  >
                    {["auto", "videotoolbox", "nvenc", "amf", "none"].map((h) => (
                      <option key={h}>{h}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 border-t border-line p-3">
            <button onClick={onClose} className="rounded-control px-4 py-2 text-sm text-ink-dim hover:text-ink">
              Abbrechen
            </button>
            <button
              onClick={save}
              className="rounded-control bg-accent px-4 py-2 text-sm text-[#0b0d10] hover:bg-accent-hi"
            >
              Speichern
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "ok" ? "bg-beat" : status === "error" ? "bg-warn" : "bg-ink-dim";
  return <span className={`h-2.5 w-2.5 rounded-full ${color}`} />;
}
