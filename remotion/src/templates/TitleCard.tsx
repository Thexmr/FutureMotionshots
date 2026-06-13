import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export interface TitleCardProps {
  headline: string;
  kicker?: string;
  accent: string;
}

export const titleCardSchema = {
  headline: { type: "string", label: "Headline", default: "Motionshot" },
  kicker: { type: "string", label: "Kicker", default: "STUDIO" },
  accent: { type: "color", label: "Akzent", default: "#6e8bff" },
} as const;

/** Full-frame intro/outro title with a mask-reveal headline. Opaque background
 *  (not keyed) — meant to fill a clip rather than overlay. */
export const TitleCard: React.FC<TitleCardProps> = ({ headline, kicker, accent }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const reveal = interpolate(frame, [0, 18], [0, 100], { extrapolateRight: "clamp" });
  const out = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0b0d10",
        justifyContent: "center",
        alignItems: "center",
        opacity: out,
      }}
    >
      {kicker && (
        <div style={{ color: accent, letterSpacing: 8, fontSize: 28, fontFamily: "Inter" }}>
          {kicker}
        </div>
      )}
      <div
        style={{
          color: "#fff",
          fontSize: 120,
          fontWeight: 800,
          fontFamily: "Inter",
          clipPath: `inset(0 ${100 - reveal}% 0 0)`,
        }}
      >
        {headline}
      </div>
    </AbsoluteFill>
  );
};
