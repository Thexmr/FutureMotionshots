import { useRef, useState } from "react";
import { useStudio } from "../../stores/studioStore";
import { api } from "../../api/client";

/** The script surface — Descript's killer feature, sharpened. Click a word to
 *  toggle cut/kept; the timeline recompiles live. Filler/pause tokens are
 *  visually distinct and removable in one click. */
export function TranscriptPanel() {
  const project = useStudio((s) => s.project);
  const transcript = useStudio((s) => s.transcript);
  const toggleWord = useStudio((s) => s.toggleWord);
  const removeFillers = useStudio((s) => s.removeFillers);
  const setPlayhead = useStudio((s) => s.setPlayhead);
  const loadProject = useStudio((s) => s.loadProject);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const importAndTranscribe = async (file: File) => {
    if (!project) return;
    setBusy(true);
    try {
      const asset = await api.uploadMedia(project.id, file);
      await api.transcribe(project.id, asset.id);
      await loadProject(project.id);
    } catch (e) {
      alert("Transkription nicht verfügbar (faster-whisper installieren). " + e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <span className="text-sm font-medium">Transkript</span>
        {transcript && (
          <button
            onClick={() => void removeFillers()}
            className="text-xs text-ink-dim hover:text-accent"
          >
            Füllwörter entfernen
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3 leading-8">
        {!transcript && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-sm text-ink-dim">
            <p>Video oder Audio importieren und automatisch transkribieren.</p>
            <button
              onClick={() => fileRef.current?.click()}
              className="rounded-control bg-accent px-4 py-2 text-[#0b0d10] hover:bg-accent-hi"
              disabled={busy}
            >
              {busy ? "Transkribiere…" : "Medien importieren"}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="video/*,audio/*"
              hidden
              onChange={(e) => e.target.files && importAndTranscribe(e.target.files[0])}
            />
          </div>
        )}

        {transcript && (
          <p className="text-[15px]">
            {transcript.words.map((w) => {
              const cut = w.state === "cut";
              const base =
                w.kind === "filler"
                  ? "text-warn"
                  : w.kind === "pause"
                    ? "text-ink-dim/50"
                    : "text-ink";
              return (
                <span
                  key={w.id}
                  onClick={() => void toggleWord(w.id)}
                  onDoubleClick={() => setPlayhead(w.start)}
                  className={`cursor-pointer rounded px-0.5 transition hover:bg-elev ${base} ${
                    cut ? "text-ink-dim/40 line-through" : ""
                  }`}
                  title={`${w.start.toFixed(2)}s`}
                >
                  {w.text}{" "}
                </span>
              );
            })}
          </p>
        )}
      </div>
    </div>
  );
}
