"""In-memory project + transcript store with JSON persistence per project.

Persistence-first (a lesson from the reference repo where timeline edits were
lost on reload): every mutation goes through here and is written to disk.
Transcripts are stored alongside projects but kept out of the Project payload
that travels on every timeline PATCH.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.project import Project, Transcript


class ProjectStore:
    def __init__(self, root: str = "storage"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._projects: dict[str, Project] = {}
        self._transcripts: dict[str, Transcript] = {}
        self._load_all()

    def _proj_path(self, pid: str) -> Path:
        return self.root / pid / "project.json"

    def _load_all(self) -> None:
        for pdir in self.root.iterdir() if self.root.exists() else []:
            pf = pdir / "project.json"
            if pf.exists():
                try:
                    self._projects[pdir.name] = Project.model_validate_json(pf.read_text())
                except Exception:
                    continue
            tdir = pdir / "transcripts"
            if tdir.exists():
                for tf in tdir.glob("*.json"):
                    try:
                        t = Transcript.model_validate_json(tf.read_text())
                        self._transcripts[t.id] = t
                    except Exception:
                        continue

    # -- projects ---------------------------------------------------------- #
    def list(self) -> list[Project]:
        return sorted(self._projects.values(), key=lambda p: p.updated_at, reverse=True)

    def get(self, pid: str) -> Optional[Project]:
        return self._projects.get(pid)

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        pdir = self.root / project.id
        pdir.mkdir(parents=True, exist_ok=True)
        self._proj_path(project.id).write_text(project.model_dump_json(indent=2))
        return project

    def delete(self, pid: str) -> bool:
        self._projects.pop(pid, None)
        pdir = self.root / pid
        if pdir.exists():
            import shutil
            shutil.rmtree(pdir, ignore_errors=True)
            return True
        return False

    # -- transcripts ------------------------------------------------------- #
    def save_transcript(self, project_id: str, transcript: Transcript) -> Transcript:
        self._transcripts[transcript.id] = transcript
        tdir = self.root / project_id / "transcripts"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / f"{transcript.id}.json").write_text(transcript.model_dump_json(indent=2))
        return transcript

    def get_transcript(self, tid: str) -> Optional[Transcript]:
        return self._transcripts.get(tid)


_store: Optional[ProjectStore] = None


def get_project_store() -> ProjectStore:
    global _store
    if _store is None:
        _store = ProjectStore()
    return _store
