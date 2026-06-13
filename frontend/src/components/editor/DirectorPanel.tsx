import { useState } from "react";
import { useStudio } from "../../stores/studioStore";
import { Inspector } from "./Inspector";

const SUGGESTIONS = [
  "Entferne alle Füllwörter und Pausen",
  "Mach daraus einen 30s-TikTok mit Beat-Cuts",
  "Setze auf jeden Drop eine Speed-Ramp",
  "Füge Kinetic-Captions hinzu und prüfe das Ergebnis visuell",
];

/** The Director — a persistent agent column (chat + action cards + vision
 *  checks), not a popup. When a clip is selected the Inspector takes over. */
export function DirectorPanel() {
  const messages = useStudio((s) => s.messages);
  const actions = useStudio((s) => s.actions);
  const checks = useStudio((s) => s.visualChecks);
  const busy = useStudio((s) => s.agentBusy);
  const sendAgent = useStudio((s) => s.sendAgent);
  const selectedClipId = useStudio((s) => s.selectedClipId);
  const [text, setText] = useState("");

  if (selectedClipId) return <Inspector />;

  const submit = () => {
    if (!text.trim() || busy) return;
    void sendAgent(text.trim());
    setText("");
  };

  return (
    <div className="panel flex h-full flex-col">
      <div className="border-b border-line px-3 py-2 text-sm font-medium">
        Director <span className="text-xs text-ink-dim">· KI-Regie</span>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && actions.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-ink-dim">
              Gib dem Agenten einen Auftrag in natürlicher Sprache:
            </p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => void sendAgent(s)}
                className="ctl block w-full px-3 py-2 text-left text-sm text-ink-dim hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-control px-3 py-2 text-sm ${
              m.role === "user" ? "bg-elev text-ink" : "bg-base text-ink"
            }`}
          >
            <div className="mb-0.5 text-[10px] uppercase tracking-wide text-ink-dim">
              {m.role === "user" ? "Du" : "Director"}
            </div>
            {m.content}
          </div>
        ))}

        {actions.map((a, i) => (
          <div key={i} className="ctl px-3 py-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-accent">{a.tool}</span>
              <span
                className={`text-[10px] ${
                  a.state === "done"
                    ? "text-beat"
                    : a.state === "failed"
                      ? "text-warn"
                      : "animate-pulse text-ink-dim"
                }`}
              >
                {a.state}
              </span>
            </div>
            {a.result_summary && (
              <p className="mt-1 text-xs text-ink-dim">{a.result_summary}</p>
            )}
          </div>
        ))}

        {checks.map((c, i) => (
          <div key={`vc-${i}`} className="ctl border-l-2 border-beat px-3 py-2 text-xs">
            <div className="flex justify-between">
              <span className="text-ink-dim">Visuelle Prüfung</span>
              <span
                className={
                  c.verdict === "pass"
                    ? "text-beat"
                    : c.verdict === "fail"
                      ? "text-warn"
                      : "text-gold"
                }
              >
                {c.verdict} · {c.score.toFixed(2)}
              </span>
            </div>
            {c.notes.map((n, j) => (
              <p key={j} className="mt-0.5 text-ink-dim">
                {n}
              </p>
            ))}
          </div>
        ))}
      </div>

      <div className="border-t border-line p-2">
        <div className="ctl flex items-end gap-2 p-1.5">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Auftrag an den Director…"
            rows={2}
            className="flex-1 resize-none bg-transparent px-2 py-1 text-sm text-ink outline-none"
          />
          <button
            onClick={submit}
            disabled={busy}
            className="rounded-control bg-accent px-3 py-1.5 text-sm text-[#0b0d10] hover:bg-accent-hi disabled:opacity-50"
          >
            {busy ? "…" : "▸"}
          </button>
        </div>
      </div>
    </div>
  );
}
