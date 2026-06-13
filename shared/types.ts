/**
 * Motionshot Studio — shared contract between frontend, backend and remotion.
 *
 * The Python models in backend/app/models mirror these shapes 1:1
 * (snake_case on the wire, camelCase here is mapped by the API client).
 *
 * Core ideas:
 *  - A MediaAsset owns a word-level Transcript.
 *  - The Timeline is the single source of truth for the edit (tracks → clips).
 *  - Text-based editing toggles Word.state; the EDL compiler turns kept word
 *    ranges into clips with word-boundary snapping and micro audio fades.
 *  - Clips carry speed ramps, transitions, effects and motion overlays.
 *  - The agent edits the same model through typed actions and verifies its
 *    work visually (frame extraction → vision model → score → retry).
 */

// ---------------------------------------------------------------------------
// Project & media
// ---------------------------------------------------------------------------

export type AspectPreset = "16:9" | "9:16" | "1:1" | "4:5" | "21:9";

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  aspect: AspectPreset;
  width: number;
  height: number;
  fps: number;
  media: MediaAsset[];
  timeline: Timeline;
  caption_settings: CaptionSettings;
  notes?: string;
  revision: number;
}

export type MediaKind = "video" | "audio" | "image" | "music" | "generated";
export type MediaOrigin =
  | "upload"
  | "record"
  | "heygen"
  | "remotion"
  | "hyperframe"
  | "stock"
  | "tts";

export interface MediaAsset {
  id: string;
  kind: MediaKind;
  origin: MediaOrigin;
  label: string;
  /** Server-side file path / URL served under /media/{id}/file */
  src: string;
  duration: number;
  width?: number;
  height?: number;
  fps?: number;
  /** Multicam: assets with the same group share a sync clock. */
  multicam_group?: string;
  /** Camera angle name inside a multicam group ("A-Cam", "B-Cam"...). */
  angle?: string;
  /** Offset (s) of this asset relative to the multicam group clock. */
  sync_offset?: number;
  transcript_id?: string;
  beat_grid_id?: string;
  waveform_ready: boolean;
  thumbnails_ready: boolean;
}

// ---------------------------------------------------------------------------
// Transcript — the text-editing surface
// ---------------------------------------------------------------------------

export type WordKind = "word" | "filler" | "pause" | "punct";
export type WordState = "kept" | "cut";

export interface Word {
  id: string;
  text: string;
  start: number;
  end: number;
  confidence: number;
  kind: WordKind;
  state: WordState;
  speaker?: string;
  /** Marks a correction the user typed; original audio stays untouched. */
  corrected?: boolean;
}

export interface SpeechSegment {
  id: string;
  speaker?: string;
  start: number;
  end: number;
  word_ids: string[];
}

export interface Transcript {
  id: string;
  media_id: string;
  language: string;
  words: Word[];
  segments: SpeechSegment[];
  /** Engine used: faster-whisper local model name or provider id. */
  engine: string;
}

// ---------------------------------------------------------------------------
// Timeline — multi-track edit model
// ---------------------------------------------------------------------------

export type TrackKind = "video" | "broll" | "overlay" | "caption" | "audio" | "music";

export interface Timeline {
  tracks: Track[];
  duration: number;
  markers: Marker[];
  /** Beat grid of the active music track, if analysed. */
  beat_grid?: BeatGrid;
}

export interface Track {
  id: string;
  kind: TrackKind;
  name: string;
  clips: Clip[];
  muted: boolean;
  locked: boolean;
  /** 0..1 — audio tracks only. */
  gain: number;
}

export type TransitionKind =
  | "none"
  | "cut"
  | "crossfade"
  | "dip-black"
  | "whip-left"
  | "whip-right"
  | "zoom-punch"
  | "glitch"
  | "film-burn";

export interface Transition {
  kind: TransitionKind;
  duration: number;
}

export interface Clip {
  id: string;
  /** Source asset; overlay clips reference a template instead. */
  media_id?: string;
  /** Timeline position (s). */
  start: number;
  /** Source in/out points (s, pre-speed). */
  in_point: number;
  out_point: number;
  /** Constant speed factor; ignored when speed_ramp is set. */
  speed: number;
  speed_ramp?: SpeedRamp;
  transition_in?: Transition;
  transition_out?: Transition;
  effects: Effect[];
  overlay?: MotionOverlay;
  /** Multicam: switch points within the clip (clip-relative seconds). */
  angle_switches?: AngleSwitch[];
  gain: number;
  /** Word ids this clip was compiled from (text-based editing link). */
  word_ids?: string[];
  label?: string;
}

export interface SpeedRampKeyframe {
  /** Clip-relative source time (s). */
  t: number;
  /** Speed factor at this point (0.1 .. 16). */
  speed: number;
}

export interface SpeedRamp {
  keyframes: SpeedRampKeyframe[];
  interpolation: "linear" | "bezier" | "hold";
  /** Keep audio pitch constant while ramping. */
  preserve_pitch: boolean;
}

export interface AngleSwitch {
  /** Clip-relative time (s). */
  t: number;
  /** Media asset id of the angle to cut to. */
  media_id: string;
}

export type EffectKind =
  | "zoom"
  | "pan"
  | "shake"
  | "blur"
  | "color-grade"
  | "vignette"
  | "chromatic"
  | "freeze";

export interface Effect {
  id: string;
  kind: EffectKind;
  /** Clip-relative start/end (s). */
  start: number;
  end: number;
  /** Effect-specific parameters (zoom: {from, to, anchor_x, anchor_y}). */
  params: Record<string, number | string | boolean>;
  easing: "linear" | "ease-in" | "ease-out" | "ease-in-out" | "spring";
}

export type MarkerKind = "beat" | "downbeat" | "chapter" | "comment" | "cue" | "flag";

export interface Marker {
  id: string;
  t: number;
  kind: MarkerKind;
  label?: string;
  color?: string;
}

export interface BeatGrid {
  media_id: string;
  bpm: number;
  /** Beat timestamps (s) in source time. */
  beats: number[];
  /** Indices into beats[] that are bar downbeats. */
  downbeats: number[];
  confidence: number;
  /** Per-beat energy 0..1 for drop detection. */
  energy: number[];
}

// ---------------------------------------------------------------------------
// Motion graphics — Remotion + Hyperframes
// ---------------------------------------------------------------------------

export type MotionEngine = "remotion" | "hyperframe";

export type MotionCategory =
  | "title"
  | "lower-third"
  | "callout"
  | "caption-style"
  | "transition"
  | "chart"
  | "social"
  | "shape"
  | "scene";

export interface MotionTemplate {
  id: string;
  engine: MotionEngine;
  category: MotionCategory;
  name: string;
  description: string;
  /** JSON-schema-ish prop spec used to build the inspector form. */
  props_schema: Record<string, MotionPropSpec>;
  default_props: Record<string, unknown>;
  duration_default: number;
  preview_color: string;
}

export interface MotionPropSpec {
  type: "string" | "number" | "color" | "boolean" | "select";
  label: string;
  default: unknown;
  min?: number;
  max?: number;
  options?: string[];
}

export interface MotionOverlay {
  template_id: string;
  engine: MotionEngine;
  props: Record<string, unknown>;
  /** Anchor inside the canvas (0..1 normalised). */
  x: number;
  y: number;
  scale: number;
}

// ---------------------------------------------------------------------------
// Captions
// ---------------------------------------------------------------------------

export type CaptionStyleId =
  | "studio"
  | "kinetic-pop"
  | "karaoke"
  | "typewriter"
  | "broadcast"
  | "bold-impact"
  | "wave"
  | "minimal"
  | "neon"
  | "documentary";

export interface CaptionSettings {
  enabled: boolean;
  style: CaptionStyleId;
  position: "bottom" | "center" | "top";
  max_words_per_line: number;
  highlight_color: string;
  base_color: string;
  font: string;
  font_size: number;
  uppercase: boolean;
  emphasize_keywords: boolean;
}

// ---------------------------------------------------------------------------
// Audio tools
// ---------------------------------------------------------------------------

export interface AudioEnhanceSettings {
  denoise: boolean;
  deess: boolean;
  loudnorm: boolean;
  target_lufs: number;
  voice_isolation: boolean;
  music_duck: boolean;
  duck_amount_db: number;
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export type ExportCodec = "h264" | "h265" | "av1" | "prores" | "vp9";

export interface ExportSettings {
  codec: ExportCodec;
  resolution: string;
  fps: number;
  bitrate_mode: "auto" | "high" | "master";
  burn_captions: boolean;
  audio_enhance: AudioEnhanceSettings;
  loudness_target: "youtube" | "tiktok" | "broadcast" | "podcast";
}

export type JobState = "queued" | "running" | "done" | "failed" | "cancelled";

export interface ExportJob {
  id: string;
  project_id: string;
  settings: ExportSettings;
  state: JobState;
  progress: number;
  stage: string;
  output_path?: string;
  error?: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// AI agent
// ---------------------------------------------------------------------------

export type AgentTaskKind =
  | "chat"
  | "edit_plan"
  | "vision_check"
  | "transcribe_polish"
  | "captions"
  | "motion_design"
  | "music_analysis"
  | "script_writing";

export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  /** Tool call rendered as an action card in the UI. */
  action?: AgentAction;
  created_at: string;
}

export interface AgentAction {
  tool: string;
  args: Record<string, unknown>;
  result_summary?: string;
  state: "running" | "done" | "failed";
  /** Snapshot id to restore if the user rejects this action. */
  checkpoint_id?: string;
}

export interface AgentVisualCheck {
  /** Timestamps (timeline s) of frames inspected. */
  frames: number[];
  verdict: "pass" | "issues" | "fail";
  score: number;
  notes: string[];
}

// ---------------------------------------------------------------------------
// Providers & model routing
// ---------------------------------------------------------------------------

export type ProviderId =
  | "anthropic"
  | "openai"
  | "ollama"
  | "openrouter"
  | "heygen"
  | "elevenlabs"
  | "pexels"
  | "pixabay";

export interface ProviderConfig {
  id: ProviderId;
  label: string;
  api_key?: string;
  base_url?: string;
  enabled: boolean;
  /** Filled by /providers/{id}/test. */
  status: "unknown" | "ok" | "error";
  status_detail?: string;
  models: string[];
}

export interface RoutingRule {
  task: AgentTaskKind | "transcription";
  provider: ProviderId | "local";
  model: string;
  fallback_provider?: ProviderId | "local";
  fallback_model?: string;
}

export interface StudioSettings {
  providers: ProviderConfig[];
  routing: RoutingRule[];
  whisper_model: "tiny" | "base" | "small" | "medium" | "large-v3";
  hardware_accel: "auto" | "videotoolbox" | "nvenc" | "amf" | "none";
  storage_dir: string;
}

// ---------------------------------------------------------------------------
// Realtime events (WebSocket /ws)
// ---------------------------------------------------------------------------

export type StudioEvent =
  | { type: "job.progress"; job_id: string; progress: number; stage: string }
  | { type: "job.done"; job_id: string; output_path: string }
  | { type: "job.failed"; job_id: string; error: string }
  | { type: "agent.message"; message: AgentMessage }
  | { type: "agent.action"; action: AgentAction }
  | { type: "agent.visual_check"; check: AgentVisualCheck }
  | { type: "transcript.ready"; media_id: string; transcript_id: string }
  | { type: "beatgrid.ready"; media_id: string }
  | { type: "timeline.updated"; revision: number };
