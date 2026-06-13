"""Persist StudioSettings to studio_settings.json and resolve task → client.

Keys live only in this file (gitignored), never logged, never hardcoded.
`resolve()` implements task-based model routing with a fallback provider.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.settings import (
    AgentTaskKind,
    ProviderConfig,
    RoutingRule,
    StudioSettings,
    default_settings,
)
from .ai_client import AIClient

SETTINGS_PATH = Path("studio_settings.json")


class SettingsStore:
    def __init__(self, path: Path = SETTINGS_PATH):
        self.path = path
        self.settings = self._load()

    def _load(self) -> StudioSettings:
        if self.path.exists():
            try:
                return StudioSettings.model_validate_json(self.path.read_text())
            except Exception:
                pass
        return default_settings()

    def save(self, settings: Optional[StudioSettings] = None) -> StudioSettings:
        if settings is not None:
            self.settings = settings
        self.path.write_text(self.settings.model_dump_json(indent=2))
        return self.settings

    # -- lookups ----------------------------------------------------------- #
    def provider(self, provider_id: str) -> Optional[ProviderConfig]:
        return next((p for p in self.settings.providers if p.id == provider_id), None)

    def rule_for(self, task: AgentTaskKind) -> Optional[RoutingRule]:
        return next((r for r in self.settings.routing if r.task == task), None)

    def client_for(self, task: AgentTaskKind) -> tuple[Optional[AIClient], str]:
        """Return (client, model) for a task, honouring routing + fallback.

        A provider is usable if it's "local" (ollama) or has an api key set.
        """
        rule = self.rule_for(task)
        if rule is None:
            return None, ""
        for provider_id, model in (
            (rule.provider, rule.model),
            (rule.fallback_provider, rule.fallback_model),
        ):
            if not provider_id:
                continue
            pid = "ollama" if provider_id == "local" and self.provider("ollama") else provider_id
            cfg = self.provider(pid)
            if cfg is None:
                continue
            usable = cfg.id == "ollama" or bool(cfg.api_key)
            if usable and model:
                return AIClient(cfg), model
        return None, ""


_store: Optional[SettingsStore] = None


def get_store() -> SettingsStore:
    global _store
    if _store is None:
        _store = SettingsStore()
    return _store
