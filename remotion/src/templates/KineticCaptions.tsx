import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface CaptionToken {
  text: string;
  startFrame: number;
  endFrame: number;
  emphasis?: boolean;
}

export interface KineticCaptionsProps {
  tokens: CaptionToken[];
  highlight: string;
  base: string;
  fontSize: number;
  uppercase: boolean;
}

export const kineticCaptionsSchema = {
  highlight: { type: "color", label: "Highlight", default: "#fcd34d" },
  base: { type: "color", label: "Basis", default: "#ffffff" },
  fontSize: { type: "number", label: "Schriftgröße", default: 72, min: 24, max: 160 },
  uppercase: { type: "boolean", label: "Großschrift", default: true },
} as const;

/** Word-by-word kinetic captions. The active word pops with a spring scale and
 *  switches to the highlight colour — the social-video caption style Descript
 *  only does in a limited way. Black key for compositing. */
export const KineticCaptions: React.FC<KineticCaptionsProps> = ({
  tokens,
  highlight,
  base,
  fontSize,
  uppercase,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const active = tokens.filter((t) => frame >= t.startFrame && frame <= t.endFrame + 6);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000",
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 220,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          maxWidth: "80%",
          justifyContent: "center",
        }}
      >
        {active.map((t, i) => {
          const isActive = frame >= t.startFrame && frame <= t.endFrame;
          const pop = spring({
            frame: frame - t.startFrame,
            fps,
            config: { damping: 12, mass: 0.4 },
          });
          const scale = interpolate(pop, [0, 1], [0.7, 1]);
          return (
            <span
              key={i}
              style={{
                fontFamily: "Inter",
                fontWeight: 800,
                fontSize,
                color: isActive || t.emphasis ? highlight : base,
                transform: `scale(${scale})`,
                textTransform: uppercase ? "uppercase" : "none",
                textShadow: "0 4px 24px rgba(0,0,0,0.6)",
              }}
            >
              {t.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
