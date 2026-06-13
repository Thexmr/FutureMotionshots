"""Word-level transcription via faster-whisper (local) with graceful fallback.

faster-whisper gives word timestamps we need for text-based editing. If it isn't
installed (e.g. CI without the model), `transcribe` raises a clear error and the
API surfaces a 503 rather than crashing — the rest of the studio still works.
"""
from __future__ import annotations

from pathlib import Path

from ..models.project import SpeechSegment, Transcript, Word
from .edl_compiler import detect_fillers

_PAUSE_GAP_S = 0.5


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def transcribe(media_id: str, audio_path: str, model_size: str = "small",
               language: str | None = None) -> Transcript:
    if not whisper_available():
        raise RuntimeError(
            "faster-whisper not installed. `pip install faster-whisper` or route "
            "transcription to OpenAI Whisper in Settings.")
    from faster_whisper import WhisperModel

    if not Path(audio_path).exists():
        raise FileNotFoundError(audio_path)

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    # vad_filter=False keeps stammers/retakes so the cleanup pass can decide.
    segments, info = model.transcribe(
        audio_path, word_timestamps=True, vad_filter=False, language=language)

    words: list[Word] = []
    speech_segments: list[SpeechSegment] = []
    prev_end = 0.0
    for seg in segments:
        seg_word_ids: list[str] = []
        for w in (seg.words or []):
            gap = w.start - prev_end
            if gap >= _PAUSE_GAP_S and words:
                pause = Word(text="·", start=prev_end, end=w.start, kind="pause",
                             confidence=1.0)
                words.append(pause)
            word = Word(text=w.word.strip(), start=round(w.start, 3),
                        end=round(w.end, 3), confidence=round(w.probability, 3))
            words.append(word)
            seg_word_ids.append(word.id)
            prev_end = w.end
        if seg_word_ids:
            speech_segments.append(SpeechSegment(
                start=round(seg.start, 3), end=round(seg.end, 3), word_ids=seg_word_ids))

    detect_fillers(words)
    return Transcript(
        media_id=media_id, language=info.language or language or "en",
        words=words, segments=speech_segments,
        engine=f"faster-whisper:{model_size}")
