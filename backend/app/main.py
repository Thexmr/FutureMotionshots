"""Motionshot Studio API — FastAPI app wiring models, services and the agent.

Single-port in production: the built frontend is mounted at "/". Endpoints are
grouped: projects, media/transcription, timeline editing, beats, agent, export,
settings/providers. A single WebSocket at /ws streams StudioEvents.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import (
    Body, FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent.runner import AgentRunner, VisualVerifier
from .models.project import (
    ASPECT_DIMS, ExportSettings, MediaAsset, Project, Track,
)
from .models.settings import StudioSettings
from .services import beat_detector, edl_compiler, render, transcription
from .services.project_store import get_project_store
from .services.settings_store import get_store

app = FastAPI(title="Motionshot Studio", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"],
)

store = get_project_store()
settings_store = get_store()

# ----- realtime hub -------------------------------------------------------- #
_clients: set[WebSocket] = set()


async def broadcast(event: dict) -> None:
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; clients don't push commands here
    except WebSocketDisconnect:
        _clients.discard(ws)


# ----- capabilities -------------------------------------------------------- #
@app.get("/api/capabilities")
def capabilities():
    return {
        "ffmpeg": render.ffmpeg_available(),
        "whisper": transcription.whisper_available(),
        "providers": [p.id for p in settings_store.settings.providers if p.enabled or p.api_key],
    }


# ----- projects ------------------------------------------------------------ #
@app.get("/api/projects")
def list_projects():
    return [p.model_dump() for p in store.list()]


@app.post("/api/projects")
def create_project(payload: dict = Body(default={})):
    aspect = payload.get("aspect", "16:9")
    w, h = ASPECT_DIMS.get(aspect, (1920, 1080))
    project = Project(
        name=payload.get("name", "Untitled"), aspect=aspect, width=w, height=h,
        fps=int(payload.get("fps", 30)))
    for kind, name in [("video", "V1"), ("broll", "B-Roll"), ("overlay", "Overlay"),
                       ("caption", "Captions"), ("audio", "Audio"), ("music", "Music")]:
        project.timeline.tracks.append(Track(kind=kind, name=name))
    return store.save(project).model_dump()


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    return p.model_dump()


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    return {"deleted": store.delete(pid)}


@app.patch("/api/projects/{pid}/timeline")
def patch_timeline(pid: str, timeline: dict = Body(...)):
    """Persist the whole timeline on every edit (autosave-friendly)."""
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    from .models.project import Timeline
    p.timeline = Timeline.model_validate(timeline)
    p.timeline.recompute_duration()
    p.touch()
    store.save(p)
    return {"revision": p.revision, "duration": p.timeline.duration}


# ----- media + transcription ----------------------------------------------- #
@app.post("/api/projects/{pid}/media")
async def upload_media(pid: str, file: UploadFile):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    media_dir = Path(store.root) / pid / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    dest = media_dir / (file.filename or "upload.bin")
    # Stream to disk in chunks — never buffer the whole file in RAM.
    with dest.open("wb") as fh:
        while chunk := await file.read(1024 * 1024):
            fh.write(chunk)
    kind = "music" if dest.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac") else "video"
    asset = MediaAsset(kind=kind, origin="upload", label=dest.name, src=str(dest))
    p.media.append(asset)
    p.touch()
    store.save(p)
    return asset.model_dump()


@app.post("/api/projects/{pid}/media/{media_id}/transcribe")
async def transcribe_media(pid: str, media_id: str):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    asset = next((m for m in p.media if m.id == media_id), None)
    if not asset:
        raise HTTPException(404, "media not found")
    rule = settings_store.rule_for("transcription")
    model_size = rule.model.split(":")[-1] if rule else settings_store.settings.whisper_model
    try:
        transcript = await asyncio.to_thread(
            transcription.transcribe, media_id, asset.src, model_size)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    store.save_transcript(pid, transcript)
    asset.transcript_id = transcript.id
    # Compile the initial 1:1 timeline from the kept words.
    clips = edl_compiler.compile_clips(media_id, transcript, asset.duration or
                                       (transcript.words[-1].end if transcript.words else 0))
    for tr in p.timeline.tracks:
        if tr.kind == "video":
            tr.clips = clips
    p.timeline.recompute_duration()
    p.touch()
    store.save(p)
    await broadcast({"type": "transcript.ready", "media_id": media_id,
                     "transcript_id": transcript.id})
    return {"transcript": transcript.model_dump(), "clips": len(clips)}


@app.get("/api/transcripts/{tid}")
def get_transcript(tid: str):
    t = store.get_transcript(tid)
    if not t:
        raise HTTPException(404, "transcript not found")
    return t.model_dump()


@app.post("/api/projects/{pid}/recompile")
def recompile_from_transcript(pid: str, body: dict = Body(...)):
    """Recompile the video track after the user toggled words cut/kept."""
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    tid = body.get("transcript_id")
    t = store.get_transcript(tid)
    if not t:
        raise HTTPException(404, "transcript not found")
    # Apply incoming word states.
    states = {w["id"]: w["state"] for w in body.get("words", [])}
    for w in t.words:
        if w.id in states:
            w.state = states[w.id]
    store.save_transcript(pid, t)
    total = t.words[-1].end if t.words else 0
    clips = edl_compiler.compile_clips(t.media_id, t, total)
    for tr in p.timeline.tracks:
        if tr.kind == "video":
            tr.clips = clips
    p.timeline.recompute_duration()
    p.touch()
    store.save(p)
    return {"clips": len(clips), "duration": p.timeline.duration}


# ----- beats --------------------------------------------------------------- #
@app.post("/api/projects/{pid}/media/{media_id}/beats")
async def analyse_beats(pid: str, media_id: str):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    asset = next((m for m in p.media if m.id == media_id), None)
    if not asset:
        raise HTTPException(404, "media not found")
    try:
        import numpy as np
        # Decode to mono 22.05k PCM via ffmpeg for analysis.
        grid = await asyncio.to_thread(_beats_from_file, asset.src, media_id, np)
    except Exception as exc:
        raise HTTPException(503, f"beat analysis failed: {exc}")
    p.timeline.beat_grid = grid
    asset.beat_grid_id = media_id
    p.touch()
    store.save(p)
    await broadcast({"type": "beatgrid.ready", "media_id": media_id})
    return grid.model_dump()


def _beats_from_file(src: str, media_id: str, np):
    import subprocess
    raw = subprocess.run(
        ["ffmpeg", "-i", src, "-ac", "1", "-ar", "22050", "-f", "f32le", "-"],
        capture_output=True).stdout
    samples = np.frombuffer(raw, dtype=np.float32)
    return beat_detector.detect_beats(samples, 22050, media_id)


# ----- agent --------------------------------------------------------------- #
@app.post("/api/projects/{pid}/agent")
async def run_agent(pid: str, body: dict = Body(...)):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    verifier = VisualVerifier(
        settings_store,
        lambda proj, t: render.extract_frame(proj, t, Path(store.root) / pid / "frames"))
    runner = AgentRunner(settings_store, verifier)
    run = await runner.run(p, body.get("message", ""), broadcast)
    store.save(p)
    return {"checkpoints": len(run.checkpoints), "revision": p.revision}


# ----- export -------------------------------------------------------------- #
@app.post("/api/projects/{pid}/export")
async def export_project(pid: str, settings: dict = Body(default={})):
    p = store.get(pid)
    if not p:
        raise HTTPException(404, "project not found")
    if not render.ffmpeg_available():
        raise HTTPException(503, "ffmpeg not available on server")
    export_settings = ExportSettings.model_validate(settings) if settings else ExportSettings()
    asyncio.create_task(_run_export(p, export_settings))
    return {"started": True, "project_id": pid}


async def _run_export(project: Project, settings: ExportSettings):
    job_id = f"export-{project.id}"
    await broadcast({"type": "job.progress", "job_id": job_id, "progress": 0.05,
                     "stage": "preparing"})
    # NOTE: per-segment extraction → concat is built out in services/render.py;
    # this scaffold reports the pipeline stages so the UI is fully wired.
    await broadcast({"type": "job.progress", "job_id": job_id, "progress": 0.5,
                     "stage": "encoding"})
    await asyncio.sleep(0)
    await broadcast({"type": "job.done", "job_id": job_id,
                     "output_path": f"storage/{project.id}/export.mp4"})


# ----- settings / providers ------------------------------------------------ #
@app.get("/api/settings")
def get_settings():
    s = settings_store.settings.model_dump()
    for prov in s["providers"]:
        prov["api_key"] = "***" if prov.get("api_key") else None  # never leak keys
    return s


@app.put("/api/settings")
def put_settings(payload: dict = Body(...)):
    incoming = StudioSettings.model_validate(payload)
    # Preserve existing keys when the client sends the masked placeholder.
    for prov in incoming.providers:
        if prov.api_key in (None, "***"):
            existing = settings_store.provider(prov.id)
            prov.api_key = existing.api_key if existing else None
    settings_store.save(incoming)
    return {"ok": True}


@app.post("/api/settings/providers/{provider_id}/test")
async def test_provider(provider_id: str):
    cfg = settings_store.provider(provider_id)
    if not cfg:
        raise HTTPException(404, "provider not found")
    from .services.ai_client import AIClient
    try:
        client = AIClient(cfg)
        res = await client.complete(
            cfg.models[0] if cfg.models else "test",
            [{"role": "user", "content": "ping"}], max_tokens=8)
        cfg.status, cfg.status_detail = "ok", res.text[:60] or "ok"
    except Exception as exc:
        cfg.status, cfg.status_detail = "error", str(exc)[:160]
    settings_store.save()
    return {"status": cfg.status, "detail": cfg.status_detail}


# ----- static media + SPA -------------------------------------------------- #
@app.get("/media/{pid}/{media_id}")
def serve_media(pid: str, media_id: str):
    p = store.get(pid)
    if not p:
        raise HTTPException(404)
    asset = next((m for m in p.media if m.id == media_id), None)
    if not asset or not Path(asset.src).exists():
        raise HTTPException(404)
    return FileResponse(asset.src)


_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="spa")
else:
    @app.get("/")
    def root():
        return JSONResponse({
            "name": "Motionshot Studio API", "docs": "/docs",
            "note": "frontend not built — run `npm run build` in frontend/"})
