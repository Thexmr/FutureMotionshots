// Render a single composition to a PNG sequence (transparent/black key) so the
// backend's ffmpeg pipeline can composite it over the timeline.
//
//   node render.mjs <spec.json> <out-dir>
//
// spec.json: { "compositionId": "...", "props": {...}, "durationInFrames"?: n }
import { bundle } from "@remotion/bundler";
import { renderFrames, selectComposition } from "@remotion/renderer";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const [, , specPath, outDir = "out"] = process.argv;
if (!specPath) {
  console.error("usage: node render.mjs <spec.json> <out-dir>");
  process.exit(1);
}

const spec = JSON.parse(readFileSync(specPath, "utf8"));

const serveUrl = await bundle({ entryPoint: resolve("src/index.ts") });
const composition = await selectComposition({
  serveUrl,
  id: spec.compositionId,
  inputProps: spec.props ?? {},
});

await renderFrames({
  serveUrl,
  composition: {
    ...composition,
    durationInFrames: spec.durationInFrames ?? composition.durationInFrames,
  },
  inputProps: spec.props ?? {},
  imageFormat: "png",
  outputDir: resolve(outDir),
  frameRange: undefined,
  onFrameUpdate: (f) => process.stdout.write(`\rframe ${f}`),
});

console.log(`\ndone → ${resolve(outDir)}`);
