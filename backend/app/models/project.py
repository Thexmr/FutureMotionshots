"""Pydantic v2 data models — mirror of shared/types.ts (snake_case on the wire).

The Timeline is the single source of truth for an edit. Text-based editing
toggles Word.state; the EDL compiler turns kept word ranges into Clips.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


AspectPreset = Literal["16:9", "9:16", "1:1", "4:5", "21:9"]
ASPECT_DIMS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "21:9": (2560, 1080),
}


# --------------------------------------------------------------------------- #
# Transcript
# --------------------------------------------------------------------------- #
class Word(BaseModel):
    id: str = Field(default_factory=_id)
    text: str
    start: float
    end: float
    confidence: float = 1.0
    kind: Literal["word", "filler", "pause", "punct"] = "word"
    state: Literal["kept", "cut"] = "kept"
    speaker: Optional[str] = None
    corrected: bool = False


class SpeechSegment(BaseModel):
    id: str = Field(default_factory=_id)
    speaker: Optional[str] = None
    start: float
    end: float
    word_ids: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    id: str = Field(default_factory=_id)
    media_id: str
    language: str = "en"
    words: list[Word] = Field(default_factory=list)
    segments: list[SpeechSegment] = Field(default_factory=list)
    engine: str = "faster-whisper:small"


# --------------------------------------------------------------------------- #
# Beat grid
# --------------------------------------------------------------------------- #
class BeatGrid(BaseModel):
    media_id: str
    bpm: float
    beats: list[float] = Field(default_factory=list)
    downbeats: list[int] = Field(default_factory=list)
    confidence: float = 0.0
    energy: list[float] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Media
# --------------------------------------------------------------------------- #
class MediaAsset(BaseModel):
    id: str = Field(default_factory=_id)
    kind: Literal["video", "audio", "image", "music", "generated"] = "video"
    origin: Literal[
        "upload", "record", "heygen", "remotion", "hyperframe", "stock", "tts"
    ] = "upload"
    label: str = ""
    src: str = ""
    duration: float = 0.0
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    multicam_group: Optional[str] = None
    angle: Optional[str] = None
    sync_offset: float = 0.0
    transcript_id: Optional[str] = None
    beat_grid_id: Optional[str] = None
    waveform_ready: bool = False
    thumbnails_ready: bool = False


# --------------------------------------------------------------------------- #
# Timeline
# --------------------------------------------------------------------------- #
class Transition(BaseModel):
    kind: Literal[
        "none", "cut", "crossfade", "dip-black", "whip-left", "whip-right",
        "zoom-punch", "glitch", "film-burn",
    ] = "cut"
    duration: float = 0.0


class SpeedRampKeyframe(BaseModel):
    t: float
    speed: float


class SpeedRamp(BaseModel):
    keyframes: list[SpeedRampKeyframe] = Field(default_factory=list)
    interpolation: Literal["linear", "bezier", "hold"] = "bezier"
    preserve_pitch: bool = True


class AngleSwitch(BaseModel):
    t: float
    media_id: str


class Effect(BaseModel):
    id: str = Field(default_factory=_id)
    kind: Literal[
        "zoom", "pan", "shake", "blur", "color-grade", "vignette", "chromatic", "freeze"
    ]
    start: float
    end: float
    params: dict[str, float | str | bool] = Field(default_factory=dict)
    easing: Literal["linear", "ease-in", "ease-out", "ease-in-out", "spring"] = "ease-in-out"


class MotionOverlay(BaseModel):
    template_id: str
    engine: Literal["remotion", "hyperframe"] = "remotion"
    props: dict = Field(default_factory=dict)
    x: float = 0.5
    y: float = 0.5
    scale: float = 1.0


class Clip(BaseModel):
    id: str = Field(default_factory=_id)
    media_id: Optional[str] = None
    start: float = 0.0
    in_point: float = 0.0
    out_point: float = 0.0
    speed: float = 1.0
    speed_ramp: Optional[SpeedRamp] = None
    transition_in: Optional[Transition] = None
    transition_out: Optional[Transition] = None
    effects: list[Effect] = Field(default_factory=list)
    overlay: Optional[MotionOverlay] = None
    angle_switches: list[AngleSwitch] = Field(default_factory=list)
    gain: float = 1.0
    word_ids: list[str] = Field(default_factory=list)
    label: Optional[str] = None

    @property
    def source_duration(self) -> float:
        return max(0.0, self.out_point - self.in_point)

    @property
    def timeline_duration(self) -> float:
        """Effective on-timeline duration accounting for constant speed."""
        if self.speed_ramp and self.speed_ramp.keyframes:
            # Average of keyframe speeds is a good-enough estimate for layout;
            # the renderer computes the exact mapping.
            speeds = [k.speed for k in self.speed_ramp.keyframes if k.speed > 0]
            avg = sum(speeds) / len(speeds) if speeds else 1.0
            return self.source_duration / max(avg, 0.01)
        return self.source_duration / max(self.speed, 0.01)


class Marker(BaseModel):
    id: str = Field(default_factory=_id)
    t: float
    kind: Literal["beat", "downbeat", "chapter", "comment", "cue", "flag"] = "cue"
    label: Optional[str] = None
    color: Optional[str] = None


class Track(BaseModel):
    id: str = Field(default_factory=_id)
    kind: Literal["video", "broll", "overlay", "caption", "audio", "music"]
    name: str
    clips: list[Clip] = Field(default_factory=list)
    muted: bool = False
    locked: bool = False
    gain: float = 1.0


class Timeline(BaseModel):
    tracks: list[Track] = Field(default_factory=list)
    duration: float = 0.0
    markers: list[Marker] = Field(default_factory=list)
    beat_grid: Optional[BeatGrid] = None

    def recompute_duration(self) -> float:
        end = 0.0
        for tr in self.tracks:
            for c in tr.clips:
                end = max(end, c.start + c.timeline_duration)
        self.duration = round(end, 3)
        return self.duration


# --------------------------------------------------------------------------- #
# Captions / Audio / Export
# --------------------------------------------------------------------------- #
class CaptionSettings(BaseModel):
    enabled: bool = True
    style: str = "studio"
    position: Literal["bottom", "center", "top"] = "bottom"
    max_words_per_line: int = 4
    highlight_color: str = "#FCD34D"
    base_color: str = "#FFFFFF"
    font: str = "Inter"
    font_size: int = 64
    uppercase: bool = False
    emphasize_keywords: bool = True


class AudioEnhanceSettings(BaseModel):
    denoise: bool = True
    deess: bool = False
    loudnorm: bool = True
    target_lufs: float = -14.0
    voice_isolation: bool = False
    music_duck: bool = False
    duck_amount_db: float = -12.0


class ExportSettings(BaseModel):
    codec: Literal["h264", "h265", "av1", "prores", "vp9"] = "h264"
    resolution: str = "1080p"
    fps: int = 30
    bitrate_mode: Literal["auto", "high", "master"] = "high"
    burn_captions: bool = True
    audio_enhance: AudioEnhanceSettings = Field(default_factory=AudioEnhanceSettings)
    loudness_target: Literal["youtube", "tiktok", "broadcast", "podcast"] = "youtube"


# --------------------------------------------------------------------------- #
# Project
# --------------------------------------------------------------------------- #
class Project(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = "Untitled"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    aspect: AspectPreset = "16:9"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    media: list[MediaAsset] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)
    caption_settings: CaptionSettings = Field(default_factory=CaptionSettings)
    notes: Optional[str] = None
    revision: int = 0

    def touch(self) -> None:
        self.updated_at = _now()
        self.revision += 1
