import { useStudio } from "../../stores/studioStore";
import { timecode } from "../../lib/format";

/** EDL-aware preview surface. v1 shows the source frame at the playhead with
 *  the project's aspect framing; the Remotion <Player> overlay layer plugs in
 *  here so motion graphics composite over the video exactly as exported. */
export function CanvasPreview() {
  const project = useStudio((s) => s.project);
  const playhead = useStudio((s) => s.playhead);
  const playing = useStudio((s) => s.playing);
  const setPlaying = useStudio((s) => s.setPlaying);
  const duration = project?.timeline.duration ?? 0;

  const aspectStyle =
    project?.aspect === "9:16"
      ? "aspect-[9/16] h-full"
      : project?.aspect === "1:1"
        ? "aspect-square h-full"
        : project?.aspect === "4:5"
          ? "aspect-[4/5] h-full"
          : "aspect-video w-full";

  return (
    <div className="panel flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 items-center justify-center bg-base p-4">
        <div
          className={`relative flex items-center justify-center overflow-hidden rounded-lg bg-black ${aspectStyle}`}
        >
          {project?.media[0] ? (
            <video
              key={project.media[0].id}
              src={`/media/${project.id}/${project.media[0].id}`}
              className="h-full w-full object-contain"
              muted
            />
          ) : (
            <span className="text-sm text-ink-dim">Kein Medium geladen</span>
          )}
          {/* Motion-graphics overlay layer mounts here (Remotion Player). */}
        </div>
      </div>

      <div className="flex items-center gap-4 border-t border-line px-4 py-2">
        <button
          onClick={() => setPlaying(!playing)}
          className="rounded-control bg-elev px-3 py-1.5 text-ink hover:text-accent"
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <span className="font-mono text-sm text-ink-dim">
          {timecode(playhead, project?.fps)} / {timecode(duration, project?.fps)}
        </span>
        <div className="flex-1" />
        <span className="text-xs text-ink-dim">{project?.aspect}</span>
      </div>
    </div>
  );
}
