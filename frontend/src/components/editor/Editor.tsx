import { useEffect } from "react";
import { useStudio } from "../../stores/studioStore";
import { TopBar } from "./TopBar";
import { TranscriptPanel } from "./TranscriptPanel";
import { CanvasPreview } from "./CanvasPreview";
import { Timeline } from "./Timeline";
import { DirectorPanel } from "./DirectorPanel";
import { StatusBar } from "./StatusBar";

export function Editor({
  onHome,
  onSettings,
}: {
  onHome: () => void;
  onSettings: () => void;
}) {
  const project = useStudio((s) => s.project);
  const setPlaying = useStudio((s) => s.setPlaying);
  const playing = useStudio((s) => s.playing);

  // Keyboard-first transport (Space = play/pause).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying(!playing);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [playing, setPlaying]);

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center text-ink-dim">
        Projekt wird geladen…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <TopBar onHome={onHome} onSettings={onSettings} />
      <div className="flex min-h-0 flex-1 gap-2 p-2">
        <div className="w-[26%] min-w-[280px]">
          <TranscriptPanel />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <CanvasPreview />
        </div>
        <div className="w-[26%] min-w-[300px]">
          <DirectorPanel />
        </div>
      </div>
      <div className="h-[34%] min-h-[220px] px-2 pb-2">
        <Timeline />
      </div>
      <StatusBar />
    </div>
  );
}
