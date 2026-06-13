import { useEffect, useState } from "react";
import { useStudio } from "../../stores/studioStore";
import { api } from "../../api/client";

export function StatusBar() {
  const revision = useStudio((s) => s.revision);
  const job = useStudio((s) => s.jobProgress);
  const project = useStudio((s) => s.project);
  const [caps, setCaps] = useState<{ ffmpeg: boolean; whisper: boolean } | null>(null);

  useEffect(() => {
    void api.capabilities().then(setCaps);
  }, []);

  return (
    <footer className="flex items-center gap-4 border-t border-line bg-panel px-4 py-1.5 text-xs text-ink-dim">
      <span>Revision {revision}</span>
      <span>Autosave aktiv</span>
      {job && (
        <span className="text-accent">
          {job.stage} · {Math.round(job.progress * 100)}%
        </span>
      )}
      <div className="flex-1" />
      {project?.timeline.beat_grid && (
        <span className="text-beat">♪ {project.timeline.beat_grid.bpm} BPM</span>
      )}
      <span className={caps?.whisper ? "text-beat" : "text-warn"}>
        whisper {caps?.whisper ? "✓" : "—"}
      </span>
      <span className={caps?.ffmpeg ? "text-beat" : "text-warn"}>
        ffmpeg {caps?.ffmpeg ? "✓" : "—"}
      </span>
    </footer>
  );
}
