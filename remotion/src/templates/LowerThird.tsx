import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface LowerThirdProps {
  title: string;
  subtitle?: string;
  accent: string;
}

export const lowerThirdSchema = {
  title: { type: "string", label: "Titel", default: "Max Mustermann" },
  subtitle: { type: "string", label: "Untertitel", default: "Creative Director" },
  accent: { type: "color", label: "Akzent", default: "#6e8bff" },
} as const;

/** Lower-third with a spring slide-in and an accent bar wipe. Rendered on a
 *  black key (#000) so the export pipeline composites it via colorkey. */
export const LowerThird: React.FC<LowerThirdProps> = ({ title, subtitle, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18, mass: 0.6 } });
  const x = interpolate(enter, [0, 1], [-60, 0]);
  const barW = interpolate(enter, [0, 1], [0, 8]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", justifyContent: "flex-end", padding: 96 }}>
      <div style={{ transform: `translateX(${x}px)`, opacity: enter, display: "flex", gap: 18 }}>
        <div style={{ width: barW, backgroundColor: accent, borderRadius: 4 }} />
        <div>
          <div style={{ color: "#fff", fontSize: 56, fontWeight: 700, fontFamily: "Inter" }}>
            {title}
          </div>
          {subtitle && (
            <div style={{ color: accent, fontSize: 30, fontWeight: 500, fontFamily: "Inter" }}>
              {subtitle}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
