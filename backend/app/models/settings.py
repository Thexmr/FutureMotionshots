"""Studio settings: providers (BYO key), task-based model routing, transcription."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ProviderId = Literal[
    "anthropic", "openai", "ollama", "openrouter",
    "heygen", "elevenlabs", "pexels", "pixabay",
]

AgentTaskKind = Literal[
    "chat", "edit_plan", "vision_check", "transcribe_polish",
    "captions", "motion_design", "music_analysis", "script_writing",
    "transcription",
]


class ProviderConfig(BaseModel):
    id: ProviderId
    label: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = False
    status: Literal["unknown", "ok", "error"] = "unknown"
    status_detail: Optional[str] = None
    models: list[str] = Field(default_factory=list)


class RoutingRule(BaseModel):
    task: AgentTaskKind
    provider: ProviderId | Literal["local"]
    model: str
    fallback_provider: Optional[ProviderId | Literal["local"]] = None
    fallback_model: Optional[str] = None


class StudioSettings(BaseModel):
    providers: list[ProviderConfig] = Field(default_factory=list)
    routing: list[RoutingRule] = Field(default_factory=list)
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3"] = "small"
    hardware_accel: Literal["auto", "videotoolbox", "nvenc", "amf", "none"] = "auto"
    storage_dir: str = "storage"


def default_settings() -> StudioSettings:
    """Local-first defaults: works offline with faster-whisper + Ollama."""
    return StudioSettings(
        providers=[
            ProviderConfig(id="anthropic", label="Anthropic Claude",
                           models=["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-8"]),
            ProviderConfig(id="openai", label="OpenAI",
                           models=["gpt-4o", "gpt-4o-mini", "o3-mini"]),
            ProviderConfig(id="ollama", label="Ollama (lokal)", enabled=True,
                           base_url="http://localhost:11434",
                           models=["qwen2.5:14b", "llama3.2-vision", "llava"]),
            ProviderConfig(id="openrouter", label="OpenRouter", base_url="https://openrouter.ai/api/v1"),
            ProviderConfig(id="heygen", label="HeyGen Avatare"),
            ProviderConfig(id="elevenlabs", label="ElevenLabs TTS"),
            ProviderConfig(id="pexels", label="Pexels Stock"),
            ProviderConfig(id="pixabay", label="Pixabay Stock"),
        ],
        routing=[
            RoutingRule(task="transcription", provider="local", model="faster-whisper:small"),
            RoutingRule(task="chat", provider="ollama", model="qwen2.5:14b",
                        fallback_provider="anthropic", fallback_model="claude-sonnet-4-6"),
            RoutingRule(task="edit_plan", provider="anthropic", model="claude-sonnet-4-6",
                        fallback_provider="ollama", fallback_model="qwen2.5:14b"),
            RoutingRule(task="vision_check", provider="ollama", model="llama3.2-vision",
                        fallback_provider="anthropic", fallback_model="claude-sonnet-4-6"),
            RoutingRule(task="music_analysis", provider="local", model="dsp"),
            RoutingRule(task="captions", provider="ollama", model="qwen2.5:14b"),
            RoutingRule(task="motion_design", provider="anthropic", model="claude-sonnet-4-6"),
            RoutingRule(task="transcribe_polish", provider="ollama", model="qwen2.5:14b"),
            RoutingRule(task="script_writing", provider="anthropic", model="claude-sonnet-4-6"),
        ],
    )
