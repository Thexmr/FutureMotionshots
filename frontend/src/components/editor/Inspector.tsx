import { useStudio } from "../../stores/studioStore";
import { timecode } from "../../lib/format";

/** Context inspector for the selected clip: speed ramp, effects, transitions,
 *  overlay props. Read-oriented in v1; controls write back through the store. */
export function Inspector() {
  const project = useStudio((s) => s.project);
  const selectedClipId = useStudio((s) => s.selectedClipId);
  const selectClip = useStudio((s) => s.selectClip);

  const clip = project?.timeline.tracks
    .flatMap((t) => t.clips)
    .find((c) => c.id === selectedClipId);

  if (!clip) return null;

  return (
    <div className="panel flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <span className="text-sm font-medium">Inspector</span>
        <button onClick={() => selectClip(null)} className="text-xs text-ink-dim hover:text-ink">
          ✕
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 text-sm">
        <Field label="Clip">
          <span className="font-mono text-xs text-ink-dim">{clip.id}</span>
        </Field>
        <Field label="Quelle In/Out">
          <span className="font-mono text-xs">
            {timecode(clip.in_point)} → {timecode(clip.out_point)}
          </span>
        </Field>
        <Field label="Geschwindigkeit">
          <span>{clip.speed_ramp ? "Ramp" : `${clip.speed.toFixed(2)}×`}</span>
        </Field>

        {clip.speed_ramp && (
          <div className="ctl p-2">
            <div className="mb-1 text-xs text-ink-dim">Speed Ramp ({clip.speed_ramp.interpolation})</div>
            {clip.speed_ramp.keyframes.map((k, i) => (
              <div key={i} className="flex justify-between font-mono text-xs">
                <span>{k.t.toFixed(2)}s</span>
                <span className="text-beat">{k.speed.toFixed(2)}×</span>
              </div>
            ))}
          </div>
        )}

        <Field label="Übergang">
          <span>{clip.transition_in?.kind ?? "cut"}</span>
        </Field>

        {clip.effects.length > 0 && (
          <div>
            <div className="mb-1 text-xs text-ink-dim">Effekte</div>
            {clip.effects.map((e) => (
              <div key={e.id} className="ctl mb-1 px-2 py-1 text-xs">
                {e.kind} · {e.easing}
              </div>
            ))}
          </div>
        )}

        {clip.overlay && (
          <div className="ctl p-2 text-xs">
            <div className="text-ink-dim">Motion Graphic</div>
            <div className="mt-1 font-mono text-accent">{clip.overlay.template_id}</div>
            <div className="text-ink-dim">{clip.overlay.engine}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-ink-dim">{label}</span>
      {children}
    </div>
  );
}
