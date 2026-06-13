"""Compile a word-level transcript into a Clip list for the timeline.

This is the heart of text-based editing: deleting a word in the script marks it
`cut`; this compiler turns the remaining `kept` words into clips. Rules learned
from the reference repo's auto_cut.py:

  * Never cut mid-word — removals snap outward to word boundaries.
  * Anti-chop — ignore removals shorter than ~400 ms so the cut sounds natural.
  * Micro audio fades (30 ms) live at clip boundaries (applied by the renderer).
"""
from __future__ import annotations

from ..models.project import Clip, Transcript, Word

WORD_SAFETY_S = 0.09          # padding to absorb transcription timing error
ANTI_CHOP_S = 0.40            # don't bother cutting removals shorter than this
FADE_S = 0.030                # boundary fade (renderer reads this)
FILLER_WORDS = {
    "uh", "um", "uhm", "erm", "ah", "eh", "like", "you know", "i mean",
    "äh", "ähm", "öh", "hmm", "halt", "also", "ne", "quasi",
}


def detect_fillers(words: list[Word]) -> None:
    """Mark obvious filler tokens in place (idempotent)."""
    for w in words:
        if w.kind == "word" and w.text.strip().lower().strip(".,!?") in FILLER_WORDS:
            w.kind = "filler"


def _merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not spans:
        return []
    spans = sorted(spans)
    out = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def removal_spans(transcript: Transcript) -> list[tuple[float, float]]:
    """Source-time spans to remove, snapped to word boundaries + anti-chopped."""
    words = transcript.words
    raw: list[tuple[float, float]] = []
    for i, w in enumerate(words):
        if w.state != "cut":
            continue
        prev_end = words[i - 1].end if i > 0 else w.start
        next_start = words[i + 1].start if i + 1 < len(words) else w.end
        # Snap outward to neighbouring word boundaries, keep tiny safety margin.
        start = max(prev_end - WORD_SAFETY_S, w.start)
        end = min(next_start + WORD_SAFETY_S, w.end + WORD_SAFETY_S)
        raw.append((start, end))

    merged = _merge_spans(raw)
    # Anti-chop: drop removals shorter than the threshold (keeps natural rhythm).
    return [(s, e) for s, e in merged if (e - s) >= ANTI_CHOP_S]


def keep_ranges(
    transcript: Transcript, total_duration: float
) -> list[tuple[float, float]]:
    """Invert removal spans → ordered (start, end) kept ranges in source time."""
    removals = removal_spans(transcript)
    ranges: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in removals:
        if s > cursor:
            ranges.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total_duration:
        ranges.append((cursor, total_duration))
    return [(s, e) for s, e in ranges if e - s > 0.01]


def _word_ids_in(transcript: Transcript, start: float, end: float) -> list[str]:
    return [
        w.id for w in transcript.words
        if w.state == "kept" and w.end > start and w.start < end
    ]


def compile_clips(
    media_id: str,
    transcript: Transcript,
    total_duration: float,
) -> list[Clip]:
    """Build timeline clips from kept word ranges. Clips keep `word_ids` so the
    timeline stays anchored to the transcript (bidirectional editing)."""
    clips: list[Clip] = []
    timeline_cursor = 0.0
    for src_start, src_end in keep_ranges(transcript, total_duration):
        dur = src_end - src_start
        clip = Clip(
            media_id=media_id,
            start=round(timeline_cursor, 3),
            in_point=round(src_start, 3),
            out_point=round(src_end, 3),
            word_ids=_word_ids_in(transcript, src_start, src_end),
        )
        clips.append(clip)
        timeline_cursor += dur
    return clips
