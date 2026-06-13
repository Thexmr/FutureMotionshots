import { useEffect, useRef } from "react";
import { useStudio } from "../../stores/studioStore";
import { clamp } from "../../lib/format";

const TRACK_H = 46;
const RULER_H = 26;
const LABEL_W = 88;
const TOKENS = {
  bg: "#0b0d10",
  panel: "#14171c",
  line: "#272c34",
  clip: "#2b3550",
  clipBorder: "#6e8bff",
  overlay: "#3a2b50",
  caption: "#4a3b1c",
  music: "#1c3a2e",
  beat: "#3ddc97",
  downbeat: "#6effb0",
  ink: "#9aa3b2",
  playhead: "#ff5470",
};

/** Canvas-rendered timeline — scales to hour-long projects without the DOM
 *  blow-up the reference repo hit. Draws ruler, beat ticks, multi-track clips,
 *  speed-ramp curves and the playhead. Click to scrub / select. */
export function Timeline() {
  const ref = useRef<HTMLCanvasElement>(null);
  const project = useStudio((s) => s.project);
  const zoom = useStudio((s) => s.zoom);
  const playhead = useStudio((s) => s.playhead);
  const selectedClipId = useStudio((s) => s.selectedClipId);
  const setPlayhead = useStudio((s) => s.setPlayhead);
  const selectClip = useStudio((s) => s.selectClip);
  const setZoom = useStudio((s) => s.setZoom);
  const revision = useStudio((s) => s.revision);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !project) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const tracks = project.timeline.tracks;
    const grid = project.timeline.beat_grid;

    // Ruler + beat grid.
    ctx.fillStyle = TOKENS.panel;
    ctx.fillRect(0, 0, rect.width, RULER_H);
    ctx.fillStyle = TOKENS.ink;
    ctx.font = "11px ui-monospace, monospace";
    const step = zoom < 50 ? 5 : zoom < 120 ? 2 : 1;
    for (let t = 0; t * zoom + LABEL_W < rect.width; t += step) {
      const x = LABEL_W + t * zoom;
      ctx.fillRect(x, RULER_H - 6, 1, 6);
      ctx.fillText(`${t}s`, x + 3, 14);
    }
    if (grid) {
      grid.beats.forEach((b, i) => {
        const x = LABEL_W + b * zoom;
        if (x < LABEL_W || x > rect.width) return;
        const down = grid.downbeats.includes(i);
        ctx.fillStyle = down ? TOKENS.downbeat : TOKENS.beat;
        ctx.globalAlpha = down ? 0.55 : 0.28;
        ctx.fillRect(x, RULER_H, 1, rect.height - RULER_H);
        ctx.globalAlpha = 1;
      });
    }

    // Tracks.
    tracks.forEach((track, ti) => {
      const y = RULER_H + ti * TRACK_H;
      ctx.fillStyle = ti % 2 ? TOKENS.bg : "#10131800";
      ctx.fillRect(0, y, rect.width, TRACK_H);
      ctx.strokeStyle = TOKENS.line;
      ctx.beginPath();
      ctx.moveTo(0, y + TRACK_H);
      ctx.lineTo(rect.width, y + TRACK_H);
      ctx.stroke();

      ctx.fillStyle = TOKENS.panel;
      ctx.fillRect(0, y, LABEL_W, TRACK_H);
      ctx.fillStyle = TOKENS.ink;
      ctx.font = "11px Inter, sans-serif";
      ctx.fillText(track.name, 8, y + TRACK_H / 2 + 4);

      const fill =
        track.kind === "overlay"
          ? TOKENS.overlay
          : track.kind === "caption"
            ? TOKENS.caption
            : track.kind === "music"
              ? TOKENS.music
              : TOKENS.clip;

      track.clips.forEach((clip) => {
        const dur =
          clip.speed_ramp && clip.speed_ramp.keyframes.length
            ? (clip.out_point - clip.in_point) /
              (clip.speed_ramp.keyframes.reduce((a, k) => a + k.speed, 0) /
                clip.speed_ramp.keyframes.length || 1)
            : (clip.out_point - clip.in_point) / (clip.speed || 1);
        const x = LABEL_W + clip.start * zoom;
        const w = Math.max(2, dur * zoom);
        const cy = y + 5;
        const ch = TRACK_H - 10;
        ctx.fillStyle = fill;
        roundRect(ctx, x, cy, w, ch, 5);
        ctx.fill();
        ctx.strokeStyle =
          clip.id === selectedClipId ? TOKENS.clipBorder : TOKENS.line;
        ctx.lineWidth = clip.id === selectedClipId ? 2 : 1;
        ctx.stroke();
        ctx.lineWidth = 1;

        // Speed-ramp curve overlay.
        if (clip.speed_ramp?.keyframes.length) {
          ctx.strokeStyle = TOKENS.beat;
          ctx.beginPath();
          clip.speed_ramp.keyframes.forEach((k, i) => {
            const kx = x + (k.t / Math.max(dur, 0.01)) * w;
            const ky = cy + ch - clamp(k.speed / 4, 0, 1) * ch;
            i === 0 ? ctx.moveTo(kx, ky) : ctx.lineTo(kx, ky);
          });
          ctx.stroke();
        }

        if (clip.label && w > 30) {
          ctx.fillStyle = "#e8ebf0";
          ctx.font = "10px Inter, sans-serif";
          ctx.fillText(clip.label.slice(0, Math.floor(w / 7)), x + 5, cy + 13);
        }
      });
    });

    // Playhead.
    const px = LABEL_W + playhead * zoom;
    ctx.fillStyle = TOKENS.playhead;
    ctx.fillRect(px, 0, 1.5, rect.height);
    ctx.beginPath();
    ctx.moveTo(px - 5, 0);
    ctx.lineTo(px + 5, 0);
    ctx.lineTo(px, 7);
    ctx.fill();
  }, [project, zoom, playhead, selectedClipId, revision]);

  const onClick = (e: React.MouseEvent) => {
    if (!project) return;
    const rect = ref.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const t = Math.max(0, (x - LABEL_W) / zoom);
    if (y < RULER_H) {
      setPlayhead(t);
      return;
    }
    const ti = Math.floor((y - RULER_H) / TRACK_H);
    const track = project.timeline.tracks[ti];
    if (track) {
      const hit = track.clips.find((c) => {
        const dur = (c.out_point - c.in_point) / (c.speed || 1);
        return t >= c.start && t <= c.start + dur;
      });
      selectClip(hit?.id ?? null);
    }
    setPlayhead(t);
  };

  return (
    <div className="panel flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-line px-3 py-1.5 text-xs text-ink-dim">
        <span>Timeline</span>
        <div className="flex-1" />
        <button onClick={() => setZoom(zoom - 20)} className="px-1 hover:text-ink">
          −
        </button>
        <span className="font-mono">{zoom}px/s</span>
        <button onClick={() => setZoom(zoom + 20)} className="px-1 hover:text-ink">
          +
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <canvas
          ref={ref}
          onClick={onClick}
          className="h-full w-full cursor-crosshair"
          style={{ minHeight: RULER_H + (project?.timeline.tracks.length ?? 6) * TRACK_H }}
        />
      </div>
    </div>
  );
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}
