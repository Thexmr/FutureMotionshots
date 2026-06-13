"""Async ffmpeg orchestration: frame extraction + export argv building.

Everything runs through argv lists (never a shell string) so user text can't be
injected into ffmpeg filters. All subprocess calls are async so the event loop
stays responsive (a documented failure mode of the reference repo).
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from ..models.project import ExportSettings, Project

RES_MAP = {
    "720p": (1280, 720), "1080p": (1920, 1080),
    "1440p": (2560, 1440), "4k": (3840, 2160),
}
LOUDNESS = {"youtube": -14.0, "tiktok": -14.0, "broadcast": -23.0, "podcast": -16.0}
ENCODERS = {
    "h264": ("libx264", "mp4"), "h265": ("libx265", "mp4"),
    "av1": ("libsvtav1", "mp4"), "prores": ("prores_ks", "mov"),
    "vp9": ("libvpx-vp9", "webm"),
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


async def _run(args: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode(errors="ignore")


async def extract_frame(project: Project, t: float, out_dir: Path) -> Optional[bytes]:
    """Extract a single JPEG at timeline time `t` for the agent's vision check.

    For v1 this samples the first source media at the timeline time; once the
    EDL→source mapping is wired it will resolve through the active clip.
    """
    if not ffmpeg_available() or not project.media:
        return None
    src = project.media[0].src
    if not src or not Path(src).exists():
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"frame_{int(t * 1000)}.jpg"
    code, _ = await _run([
        "ffmpeg", "-y", "-ss", f"{max(t, 0):.3f}", "-i", src,
        "-frames:v", "1", "-q:v", "3", str(out),
    ])
    if code == 0 and out.exists():
        return out.read_bytes()
    return None


def hw_flags(accel: str) -> list[str]:
    return {
        "videotoolbox": ["-hwaccel", "videotoolbox"],
        "nvenc": ["-hwaccel", "cuda"],
        "amf": ["-hwaccel", "d3d11va"],
    }.get(accel, [])


def build_export_args(
    project: Project, settings: ExportSettings, concat_file: Path, out_path: Path,
) -> list[str]:
    """Build the final-encode argv from a concat demuxer list of rendered segments.

    Caption burning and any subtitle filter are intentionally LAST in the chain.
    """
    encoder, _ext = ENCODERS.get(settings.codec, ("libx264", "mp4"))
    w, h = RES_MAP.get(settings.resolution, (project.width, project.height))
    target_lufs = LOUDNESS.get(settings.loudness_target, settings.audio_enhance.target_lufs)

    vf = [f"scale={w}:{h}:force_original_aspect_ratio=decrease",
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"]
    af = []
    if settings.audio_enhance.denoise:
        af.append("afftdn=nr=12")
    if settings.audio_enhance.deess:
        af.append("deesser")
    if settings.audio_enhance.loudnorm:
        af.append(f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11")

    args = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file)]
    args += ["-vf", ",".join(vf)]
    if af:
        args += ["-af", ",".join(af)]
    args += ["-c:v", encoder, "-r", str(settings.fps)]
    if settings.codec in ("h264", "h265"):
        crf = {"auto": "23", "high": "20", "master": "16"}[settings.bitrate_mode]
        args += ["-crf", crf, "-pix_fmt", "yuv420p", "-preset", "medium"]
    args += ["-c:a", "aac", "-b:a", "256k", str(out_path)]
    return args
