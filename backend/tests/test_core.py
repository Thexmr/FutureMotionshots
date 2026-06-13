"""Core logic tests: EDL compiler rules, beat detection, routing, agent tools."""
import numpy as np
import pytest

from app.models.project import Clip, Project, Track, Transcript, Word
from app.models.settings import default_settings
from app.services import beat_detector, edl_compiler
from app.services.settings_store import SettingsStore
import app.agent.tools as tools


def _transcript(*specs) -> Transcript:
    words = [Word(text=t, start=s, end=e, kind=k, state=st) for (t, s, e, k, st) in specs]
    return Transcript(media_id="m", words=words)


def test_edl_never_cuts_midword_and_anti_chops():
    # A 0.1s "cut" word is shorter than ANTI_CHOP_S → must NOT create a cut.
    t = _transcript(
        ("a", 0.0, 0.5, "word", "kept"),
        ("b", 0.5, 0.6, "word", "cut"),  # tiny removal → anti-chopped
        ("c", 0.6, 1.2, "word", "kept"),
    )
    clips = edl_compiler.compile_clips("m", t, 1.2)
    assert len(clips) == 1, "tiny removal should be ignored (anti-chop)"


def test_edl_removes_long_filler_and_keeps_word_ids():
    t = _transcript(
        ("hello", 0.0, 0.5, "word", "kept"),
        ("uhhhh", 0.5, 1.3, "filler", "cut"),  # 0.8s → real cut
        ("world", 1.3, 1.9, "word", "kept"),
    )
    clips = edl_compiler.compile_clips("m", t, 1.9)
    assert len(clips) == 2
    kept_ids = {wid for c in clips for wid in c.word_ids}
    assert t.words[0].id in kept_ids and t.words[2].id in kept_ids
    assert t.words[1].id not in kept_ids


def test_detect_fillers_marks_um():
    t = _transcript(("um", 0.0, 0.3, "word", "kept"), ("ok", 0.3, 0.6, "word", "kept"))
    edl_compiler.detect_fillers(t.words)
    assert t.words[0].kind == "filler"
    assert t.words[1].kind == "word"


def test_beat_detection_finds_120bpm():
    sr = 22050
    dur = 4.0
    sig = np.zeros(int(sr * dur), dtype=np.float32)
    for b in np.arange(0, dur, 0.5):  # 120 BPM
        i = int(b * sr)
        sig[i : i + 200] = 1.0
    grid = beat_detector.detect_beats(sig, sr, "mus")
    assert 110 <= grid.bpm <= 130
    assert len(grid.beats) > 4


def test_beat_snap_and_density():
    grid = beat_detector.BeatGrid(media_id="m", bpm=120, beats=[0.0, 0.5, 1.0, 1.5],
                                  downbeats=[0], energy=[0.9, 0.2, 0.5, 0.1])
    assert beat_detector.nearest_beat(grid, 0.62) == 0.5
    assert beat_detector.cut_density_for_energy(0.9) == 1
    assert beat_detector.cut_density_for_energy(0.1) == 8


def test_routing_local_first_and_fallback():
    store = SettingsStore.__new__(SettingsStore)
    store.settings = default_settings()
    store.path = None
    # transcription routes to local (no key needed)
    rule = store.rule_for("transcription")
    assert rule.provider == "local"
    # edit_plan prefers anthropic but with no key falls back to ollama (usable)
    client, model = store.client_for("edit_plan")
    assert client is not None and client.id == "ollama"


def test_agent_tools_mutate_timeline():
    p = Project(name="t")
    track = Track(kind="video", name="V1")
    track.clips.append(Clip(media_id="m", in_point=0, out_point=5))
    p.timeline.tracks.append(track)
    cid = track.clips[0].id

    assert "zoom" in tools.execute("add_zoom", p, {"clip_id": cid})
    assert track.clips[0].effects[0].kind == "zoom"

    tools.execute("add_speed_ramp", p, {"clip_id": cid,
                  "keyframes": [{"t": 0, "speed": 1}, {"t": 2, "speed": 0.4}]})
    assert track.clips[0].speed_ramp is not None

    out = tools.execute("inspect_frames", p, {"times": [1.0, 2.0]})
    assert out.startswith("VISION_CHECK:")


def test_motion_graphic_placement():
    p = Project(name="t")
    tools.execute("place_motion_graphic", p,
                  {"template_id": "lower-third", "start": 2.0, "duration": 3.0})
    overlay_track = next(t for t in p.timeline.tracks if t.kind == "overlay")
    assert overlay_track.clips[0].overlay.template_id == "lower-third"
