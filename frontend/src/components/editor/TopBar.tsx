import { useStudio, type EditorMode } from "../../stores/studioStore";
import { api } from "../../api/client";

const MODES: { id: EditorMode; label: string }[] = [
  { id: "auto", label: "Auto" },
  { id: "manual", label: "Manuell" },
  { id: "director", label: "Regie" },
];

export function TopBar({
  onHome,
  onSettings,
}: {
  onHome: () => void;
  onSettings: () => void;
}) {
  const project = useStudio((s) => s.project);
  const mode = useStudio((s) => s.mode);
  const setMode = useStudio((s) => s.setMode);

  const exportNow = () => {
    if (project) void api.export(project.id, { codec: "h264", resolution: "1080p" });
  };

  return (
    <header className="flex items-center justify-between border-b border-line bg-panel px-4 py-2">
      <div className="flex items-center gap-3">
        <button onClick={onHome} className="text-ink-dim hover:text-ink" title="Projekte">
          ◀
        </button>
        <span className="font-medium">{project?.name}</span>
        <span className="text-xs text-ink-dim">
          {project?.aspect} · {project?.fps}fps
        </span>
      </div>

      <div className="ctl flex overflow-hidden p-0.5">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`rounded-[6px] px-4 py-1.5 text-sm transition ${
              mode === m.id ? "bg-accent text-[#0b0d10]" : "text-ink-dim hover:text-ink"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={exportNow}
          className="rounded-control bg-accent px-4 py-1.5 text-sm font-medium text-[#0b0d10] hover:bg-accent-hi"
        >
          Export ▸
        </button>
        <button onClick={onSettings} className="text-ink-dim hover:text-ink" title="Einstellungen">
          ⚙
        </button>
      </div>
    </header>
  );
}
