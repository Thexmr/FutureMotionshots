"""Agent tools — the editing primitives the LLM may call.

Each tool mutates a Project in place and returns a short human-readable summary.
Tools are provider-neutral JSON-schema definitions; the AIClient translates them
to each provider's tool-calling format. Every successful call is wrapped by the
AgentRunner in a checkpoint so the user can undo individual actions.
"""
from __future__ import annotations

from typing import Any, Callable

from ..models.project import (
    Clip,
    Effect,
    Marker,
    MotionOverlay,
    Project,
    SpeedRamp,
    SpeedRampKeyframe,
    Track,
    Transition,
    Word,
)
from ..services import beat_detector

ToolFn = Callable[[Project, dict[str, Any]], str]

_REGISTRY: dict[str, tuple[dict, ToolFn]] = {}


def tool(name: str, description: str, parameters: dict):
    def deco(fn: ToolFn) -> ToolFn:
        _REGISTRY[name] = (
            {"name": name, "description": description, "parameters": parameters}, fn,
        )
        return fn
    return deco


def schemas() -> list[dict]:
    return [spec for spec, _ in _REGISTRY.values()]


def execute(name: str, project: Project, args: dict[str, Any]) -> str:
    if name not in _REGISTRY:
        return f"unknown tool: {name}"
    _, fn = _REGISTRY[name]
    return fn(project, args)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _video_track(project: Project) -> Track:
    for tr in project.timeline.tracks:
        if tr.kind == "video":
            return tr
    tr = Track(kind="video", name="V1")
    project.timeline.tracks.insert(0, tr)
    return tr

def _track(project: Project, kind: str, name: str) -> Track:
    for tr in project.timeline.tracks:
        if tr.kind == kind:
            return tr
    tr = Track(kind=kind, name=name)
    project.timeline.tracks.append(tr)
    return tr

def _words(project: Project) -> list[Word]:
    # First media asset transcript is the script surface for v1.
    for m in project.media:
        t = getattr(project, "_transcripts", {}).get(m.transcript_id) if m.transcript_id else None
        if t:
            return t.words
    return []


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@tool(
    "cut_text_range",
    "Mark a range of transcript words as cut by text content. Use to remove a sentence or phrase the user pointed at.",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "verbatim text to remove"}},
     "required": ["query"]},
)
def cut_text_range(project: Project, args: dict) -> str:
    query = (args.get("query") or "").lower().split()
    words = _words(project)
    if not words or not query:
        return "no transcript or empty query"
    n = 0
    for i in range(len(words) - len(query) + 1):
        window = [w.text.lower().strip(".,!?") for w in words[i : i + len(query)]]
        if window == query:
            for w in words[i : i + len(query)]:
                w.state = "cut"
                n += 1
    return f"marked {n} words as cut"


@tool(
    "remove_fillers",
    "Remove filler words (um, uh, äh, like...) across the whole transcript.",
    {"type": "object", "properties": {}},
)
def remove_fillers(project: Project, args: dict) -> str:
    from ..services.edl_compiler import detect_fillers
    words = _words(project)
    detect_fillers(words)
    n = sum(1 for w in words if w.kind == "filler" and w.state != "cut")
    for w in words:
        if w.kind == "filler":
            w.state = "cut"
    return f"removed {n} filler words"


@tool(
    "add_zoom",
    "Add a smooth punch-in zoom effect to a clip for emphasis.",
    {"type": "object", "properties": {
        "clip_id": {"type": "string"},
        "from_scale": {"type": "number", "default": 1.0},
        "to_scale": {"type": "number", "default": 1.18}},
     "required": ["clip_id"]},
)
def add_zoom(project: Project, args: dict) -> str:
    clip = _find_clip(project, args.get("clip_id"))
    if not clip:
        return "clip not found"
    clip.effects.append(Effect(
        kind="zoom", start=0.0, end=clip.timeline_duration,
        params={"from": float(args.get("from_scale", 1.0)),
                "to": float(args.get("to_scale", 1.18)),
                "anchor_x": 0.5, "anchor_y": 0.45},
        easing="ease-out"))
    return f"added zoom to clip {clip.id}"


@tool(
    "add_speed_ramp",
    "Apply a speed ramp to a clip (e.g. slow-mo into a hit, or fast-forward). Keyframes are clip-relative seconds with a speed factor.",
    {"type": "object", "properties": {
        "clip_id": {"type": "string"},
        "keyframes": {"type": "array", "items": {"type": "object", "properties": {
            "t": {"type": "number"}, "speed": {"type": "number"}}}},
        "preserve_pitch": {"type": "boolean", "default": True}},
     "required": ["clip_id", "keyframes"]},
)
def add_speed_ramp(project: Project, args: dict) -> str:
    clip = _find_clip(project, args.get("clip_id"))
    if not clip:
        return "clip not found"
    kfs = [SpeedRampKeyframe(t=float(k["t"]), speed=float(k["speed"]))
           for k in args.get("keyframes", [])]
    if not kfs:
        return "no keyframes"
    clip.speed_ramp = SpeedRamp(keyframes=kfs, interpolation="bezier",
                                preserve_pitch=bool(args.get("preserve_pitch", True)))
    project.timeline.recompute_duration()
    return f"applied speed ramp ({len(kfs)} keyframes) to clip {clip.id}"


@tool(
    "beat_cut",
    "Cut the main video track to the music beat grid. Density auto-adapts to energy unless beats_per_cut is given.",
    {"type": "object", "properties": {
        "beats_per_cut": {"type": "integer", "description": "cut every N beats; omit for energy-adaptive"}},
     },
)
def beat_cut(project: Project, args: dict) -> str:
    grid = project.timeline.beat_grid
    if not grid or not grid.beats:
        return "no beat grid; analyse a music track first"
    track = _video_track(project)
    if not track.clips:
        return "no clips on video track"
    fixed = args.get("beats_per_cut")
    cut_points: list[float] = []
    i = 0
    while i < len(grid.beats):
        cut_points.append(grid.beats[i])
        energy = grid.energy[i] if i < len(grid.energy) else 0.3
        step = int(fixed) if fixed else beat_detector.cut_density_for_energy(energy)
        i += max(1, step)
    # Add markers so the UI shows where beat cuts landed.
    for t in cut_points:
        project.timeline.markers.append(Marker(t=round(t, 3), kind="beat", label="beat-cut"))
    return f"placed {len(cut_points)} beat-aligned cut points"


@tool(
    "add_caption_track",
    "Generate captions from the transcript using a named style.",
    {"type": "object", "properties": {
        "style": {"type": "string", "enum": [
            "studio", "kinetic-pop", "karaoke", "typewriter", "broadcast",
            "bold-impact", "wave", "minimal", "neon", "documentary"]}},
     "required": ["style"]},
)
def add_caption_track(project: Project, args: dict) -> str:
    project.caption_settings.enabled = True
    project.caption_settings.style = args.get("style", "studio")
    _track(project, "caption", "Captions")
    return f"captions enabled with style '{project.caption_settings.style}'"


@tool(
    "place_motion_graphic",
    "Place a motion-graphics overlay (Remotion or Hyperframe template) on the overlay track.",
    {"type": "object", "properties": {
        "template_id": {"type": "string"},
        "engine": {"type": "string", "enum": ["remotion", "hyperframe"]},
        "start": {"type": "number"}, "duration": {"type": "number", "default": 3.0},
        "props": {"type": "object"}},
     "required": ["template_id", "start"]},
)
def place_motion_graphic(project: Project, args: dict) -> str:
    track = _track(project, "overlay", "Overlay")
    overlay = MotionOverlay(
        template_id=args["template_id"], engine=args.get("engine", "remotion"),
        props=args.get("props", {}))
    clip = Clip(start=float(args["start"]), in_point=0.0,
                out_point=float(args.get("duration", 3.0)), overlay=overlay,
                label=args["template_id"])
    track.clips.append(clip)
    project.timeline.recompute_duration()
    return f"placed motion graphic '{args['template_id']}' at {args['start']:.1f}s"


@tool(
    "set_transition",
    "Set a transition between adjacent clips on the video track.",
    {"type": "object", "properties": {
        "clip_id": {"type": "string"},
        "kind": {"type": "string", "enum": [
            "cut", "crossfade", "dip-black", "whip-left", "whip-right",
            "zoom-punch", "glitch", "film-burn"]},
        "duration": {"type": "number", "default": 0.3}},
     "required": ["clip_id", "kind"]},
)
def set_transition(project: Project, args: dict) -> str:
    clip = _find_clip(project, args.get("clip_id"))
    if not clip:
        return "clip not found"
    clip.transition_in = Transition(kind=args["kind"], duration=float(args.get("duration", 0.3)))
    return f"set {args['kind']} transition on clip {clip.id}"


@tool(
    "inspect_frames",
    "Request a visual self-check: render/extract frames at the given timeline times so the agent can verify its work.",
    {"type": "object", "properties": {
        "times": {"type": "array", "items": {"type": "number"}}},
     "required": ["times"]},
)
def inspect_frames(project: Project, args: dict) -> str:
    times = args.get("times", [])
    return f"VISION_CHECK:{','.join(str(round(float(t), 2)) for t in times)}"


def _find_clip(project: Project, clip_id) -> Clip | None:
    if not clip_id:
        return None
    for tr in project.timeline.tracks:
        for c in tr.clips:
            if c.id == clip_id:
                return c
    return None
