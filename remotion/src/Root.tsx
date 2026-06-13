import { Composition } from "remotion";
import { LowerThird } from "./templates/LowerThird";
import { KineticCaptions } from "./templates/KineticCaptions";
import { TitleCard } from "./templates/TitleCard";

/** Composition registry. The backend selects a composition by id and passes
 *  defaultProps via the render spec; the studio preview uses @remotion/player
 *  against the same components. */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="lower-third"
        component={LowerThird}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ title: "Max Mustermann", subtitle: "Creative Director", accent: "#6e8bff" }}
      />
      <Composition
        id="kinetic-captions"
        component={KineticCaptions}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          tokens: [
            { text: "Das", startFrame: 0, endFrame: 12 },
            { text: "ist", startFrame: 12, endFrame: 24 },
            { text: "Motionshot", startFrame: 24, endFrame: 48, emphasis: true },
          ],
          highlight: "#fcd34d",
          base: "#ffffff",
          fontSize: 72,
          uppercase: true,
        }}
      />
      <Composition
        id="title-card"
        component={TitleCard}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ headline: "Motionshot", kicker: "STUDIO", accent: "#6e8bff" }}
      />
    </>
  );
};
