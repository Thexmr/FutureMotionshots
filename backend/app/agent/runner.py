"""AgentRunner — tool-calling loop with checkpoints and visual self-verification.

Flow per user command:
  1. Build system prompt + tool schemas + a compact timeline snapshot.
  2. Ask the routed LLM. While it returns tool calls:
       - snapshot the project (checkpoint, enables per-action undo)
       - execute the tool, feed the result back
       - if the tool asks for a vision check, run the VisualVerifier and feed
         the verdict back so the model can self-correct.
  3. Stop when the model returns a final text answer (or max steps reached).

Events are emitted via the injected `emit` callback (wired to the WebSocket).
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from ..models.project import Project
from ..services.settings_store import SettingsStore
from . import tools

EmitFn = Callable[[dict], Awaitable[None]]

SYSTEM_PROMPT = """You are the Director, the editing agent inside Motionshot Studio.
You edit a video by calling tools on its timeline. The user works in three synced
views: transcript, canvas preview and timeline.

Principles:
- Prefer deterministic, reversible edits. One tool call = one intent.
- After a visually significant change (zoom, speed ramp, motion graphic,
  transition), call `inspect_frames` to verify the result actually looks right,
  then adjust if the verdict reports issues.
- Snap cuts to word boundaries (the cut tools already do this) and to beats for
  music-driven edits.
- When done, give the user a one-paragraph summary of what you changed.
Be concise. Do not invent clip ids; use the ones from the timeline snapshot."""


@dataclass
class Checkpoint:
    label: str
    snapshot: dict


@dataclass
class AgentRun:
    messages: list[dict] = field(default_factory=list)
    checkpoints: list[Checkpoint] = field(default_factory=list)


class VisualVerifier:
    """Extract frames at given timeline times and ask a vision model to score them."""

    def __init__(self, store: SettingsStore, frame_extractor):
        self.store = store
        self.extract = frame_extractor  # async (project, t) -> jpeg bytes | None

    async def check(self, project: Project, times: list[float]) -> dict:
        client, model = self.store.client_for("vision_check")
        notes: list[str] = []
        score = 0.5
        if client is None:
            return {"verdict": "skipped", "score": 0.0,
                    "notes": ["no vision model routed"], "frames": times}
        scores: list[float] = []
        for t in times[:4]:
            img = await self.extract(project, t)
            if not img:
                continue
            prompt = (
                "You are a video QA reviewer. Rate this frame 0-1 for: correct "
                "framing, no clipping/letterboxing artifacts, legible captions/"
                "overlays. Reply as JSON {\"score\": <0-1>, \"note\": \"...\"}.")
            try:
                raw = await client.vision(model, prompt, img)
                parsed = _extract_json(raw)
                scores.append(float(parsed.get("score", 0.5)))
                if parsed.get("note"):
                    notes.append(f"{t:.1f}s: {parsed['note']}")
            except Exception as exc:  # vision is best-effort
                notes.append(f"{t:.1f}s: vision error ({exc})")
        if scores:
            score = sum(scores) / len(scores)
        verdict = "pass" if score >= 0.8 else "issues" if score >= 0.5 else "fail"
        return {"verdict": verdict, "score": round(score, 3),
                "notes": notes, "frames": times}


class AgentRunner:
    def __init__(self, store: SettingsStore, verifier: Optional[VisualVerifier] = None):
        self.store = store
        self.verifier = verifier

    async def run(
        self,
        project: Project,
        user_message: str,
        emit: EmitFn,
        max_steps: int = 8,
    ) -> AgentRun:
        client, model = self.store.client_for("edit_plan")
        run = AgentRun()
        if client is None:
            await emit({"type": "agent.message", "message": {
                "role": "assistant",
                "content": "No model is routed for editing. Add a provider key or "
                           "enable Ollama in Settings → Routing."}})
            return run

        run.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": "Timeline snapshot:\n" + _snapshot(project)},
            {"role": "user", "content": user_message},
        ]
        tool_schemas = tools.schemas()

        for _ in range(max_steps):
            result = await client.complete(model, run.messages, tools=tool_schemas)
            if result.text:
                await emit({"type": "agent.message",
                            "message": {"role": "assistant", "content": result.text}})
            if not result.tool_calls:
                break

            run.messages.append({"role": "assistant", "content": result.text or "",
                                 "tool_calls_meta": [tc.name for tc in result.tool_calls]})

            for call in result.tool_calls:
                run.checkpoints.append(Checkpoint(
                    label=call.name, snapshot=copy.deepcopy(project.model_dump())))
                await emit({"type": "agent.action", "action": {
                    "tool": call.name, "args": call.args, "state": "running",
                    "checkpoint_id": str(len(run.checkpoints) - 1)}})

                summary = tools.execute(call.name, project, call.args)
                project.touch()

                # Visual self-verification hook.
                if summary.startswith("VISION_CHECK:") and self.verifier:
                    times = [float(x) for x in summary.split(":", 1)[1].split(",") if x]
                    check = await self.verifier.check(project, times)
                    await emit({"type": "agent.visual_check", "check": check})
                    summary = (f"vision verdict={check['verdict']} "
                               f"score={check['score']} notes={check['notes']}")

                await emit({"type": "agent.action", "action": {
                    "tool": call.name, "args": call.args,
                    "result_summary": summary, "state": "done"}})
                run.messages.append({
                    "role": "tool", "name": call.name,
                    "content": json.dumps({"result": summary})})

        await emit({"type": "timeline.updated", "revision": project.revision})
        return run


def _snapshot(project: Project) -> str:
    lines = [f"project '{project.name}' {project.aspect} {project.fps}fps "
             f"duration={project.timeline.duration:.1f}s"]
    for tr in project.timeline.tracks:
        lines.append(f"track {tr.kind} '{tr.name}': "
                     + ", ".join(f"{c.id}[{c.start:.1f}-{c.start + c.timeline_duration:.1f}]"
                                 for c in tr.clips[:12]))
    if project.timeline.beat_grid:
        g = project.timeline.beat_grid
        lines.append(f"beatgrid bpm={g.bpm} beats={len(g.beats)}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}
