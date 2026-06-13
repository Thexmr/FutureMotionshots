# Architektur: Motionshot Studio

## 1. Überblick

Monorepo mit drei Säulen + geteiltem Vertrag:

```
FutureMotionshots/
├── shared/types.ts        Single source of truth (Frontend ↔ Backend ↔ Remotion)
├── backend/               FastAPI (Python 3.11+) — Daten, KI, Rendering
├── frontend/              React 18 + TS + Vite + Tailwind — Premium-UI
├── remotion/              Remotion 4 — datengetriebene Motion-Graphics-Templates
└── docs/                  Benchmark, Konzept, Architektur, UI-Design
```

Deployment: Production servt das gebaute Frontend über das Backend (Single-Port,
`:8787`). Dev: Vite `:5173` + Uvicorn `:8787` mit Proxy.

## 2. Datenmodell (Kern)

Definiert in `shared/types.ts`, gespiegelt als Pydantic v2 in
`backend/app/models/`. Die **Timeline** ist die einzige Wahrheit des Schnitts:

```
Project → MediaAsset[] (+ Transcript, BeatGrid)
        → Timeline → Track[] → Clip[]
                                 ├ in/out, start, speed, speed_ramp
                                 ├ transition_in/out, effects[] (keyframed)
                                 ├ overlay (MotionOverlay → Remotion/Hyperframe)
                                 ├ angle_switches[] (Multicam)
                                 └ word_ids[] (Link zum Transkript)
```

Wichtige Designentscheidungen vs. Referenz-Repo:
- **Speed Ramps, Beatgrid, Multicam, Keyframe-Effekte sind nativ** (im Repo fehlten sie).
- **Clip ↔ Transkript-Link** (`word_ids`) macht Text- und Timeline-Edit bidirektional.
- **Persistenz zuerst**: jede Edit-Operation geht über die API; Autosave + Revisionen.

## 3. EDL-Compiler (Text → Schnitt)

Pipeline beim textbasierten Schneiden (`backend/app/services/edl_compiler.py`):

1. Sammle `kept`-Wortbereiche aus dem Transkript.
2. **Snap-to-word**: Lücken auf `prev.end → next.start` ausdehnen, nie mid-word.
3. **Anti-Chop**: Entfernungen < ~400 ms verwerfen (natürlicher Rhythmus).
4. Mikro-Fades (30 ms) an jeder Clip-Grenze.
5. Erzeuge Clips mit `word_ids`-Rückverweis → Timeline bleibt am Text verankert.

Fallback ohne Transkript: Energy-Gate-Stilledetektion (RMS pro 20 ms, −40 dBFS).

## 4. Audio: Beatgrid & Enhancement

- `beat_detector.py`: Onset/Tempo aus PCM (NumPy-Autokorrelation des Energie-
  Envelopes; pluggable gegen librosa/madmom). Liefert `BeatGrid`
  (bpm, beats, downbeats, energy) → Beat-Snap & Drop-Detection.
- `audio_enhance.py`: ffmpeg-Ketten — `afftdn` (Denoise), `deesser`,
  `loudnorm` (LUFS-Targets je Plattform), Side-Chain-Ducking für Musik.

## 5. KI-Agent (Tool-Calling + Vision-Loop)

`backend/app/agent/` — echter Agent statt fixer Pipeline:

```
User-Befehl ──► AgentRunner (Provider per Routing-Regel)
                  │  System-Prompt + Tool-Schemas + Timeline-Snapshot
                  ▼
            LLM wählt Tool ──► ToolRegistry.execute()  (mutiert Timeline)
                  │                 │ erzeugt Checkpoint (Undo)
                  ▼                 ▼
            ggf. mehrere Tool-Calls │ StudioEvent → WS → UI (Action-Card)
                  │
                  ▼
          VisualVerifier: Frames der betroffenen Stelle rendern/extrahieren
                  → Vision-Modell bewertet (0..1) → bei < Schwelle: Retry/Abbruch
```

Tools (Auszug, `agent/tools/`): `cut_text_range`, `remove_fillers`,
`add_zoom`, `add_speed_ramp`, `beat_cut`, `add_caption`, `place_motion_graphic`,
`reframe`, `enhance_audio`, `set_transition`, `inspect_frames`.

Tool-Schemas werden providerneutral definiert und für Anthropic/OpenAI/Ollama
übersetzt (`ai_client.py`). Jede Aktion ist ein Checkpoint → granulares Undo.

## 6. Modell-Routing & Provider

`providers.py` (BYO-Key, in `studio_settings.json`, gitignored) + `routing.py`:

| Aufgabe | Standard lokal | Standard Cloud |
|---|---|---|
| transcription | faster-whisper `small` | OpenAI Whisper |
| chat/edit_plan | Ollama (z. B. Qwen) | Anthropic Claude |
| vision_check | Ollama llava/vision | Claude/GPT Vision |
| transcribe_polish | Ollama | Claude |
| music_analysis | lokal (DSP) | — |

`RoutingRule` mit Fallback-Provider; 401/403 → kein Retry, sonst Backoff.

## 7. Rendering & Export

`render.py` + Job-Queue (`jobs.py`):
- **Async ffmpeg** durchgängig (`asyncio.create_subprocess_exec`), echter
  Fortschritt (Frame-Zählung), **cancelbar**.
- Pro-Segment-Extract → verlustarme Intermediates → Concat-Demuxer → Final-Encode.
- **MG-Compositing**: Remotion/Hyperframe-Frames werden einmalig vorgerendert
  (Headless-Chromium, `document.getAnimations().currentTime`-Seek pro Frame),
  dann via `colorkey=0x000000` + `-pix_fmt yuv420p` über die Clips gelegt.
- Codecs: h264/h265/av1/prores/vp9; Hardware-Accel: VideoToolbox/NVENC/AMF.
- Captions/Untertitel **immer zuletzt** in der Filterkette.

## 8. Motion Graphics

- **Remotion** (`remotion/`): `<Composition>` pro Template, props-getrieben.
  Vorschau im Editor via `@remotion/player`; Render serverseitig via
  `@remotion/renderer` (oder PNG-Sequenz + ffmpeg-Composite).
- **Hyperframes**: beliebige HTML/CSS-Designs, gleiches Frame-Seek-Verfahren.
- **HeyGen**: REST — Video erstellen → Status pollen → MP4 laden → als
  `MediaAsset(origin="heygen")` registrieren → in Timeline.

> Lizenzhinweis: Remotion erfordert ab bestimmter Unternehmensgröße eine
> kommerzielle Lizenz (Company License). Vor kommerziellem Launch prüfen.

## 9. Realtime

Eine WebSocket-Route `/ws` streamt `StudioEvent` (Job-Fortschritt,
Agent-Messages/Actions, Vision-Checks, Transcript-/Beatgrid-ready). UI hört zu
und rendert Action-Cards + Fortschritt live.

## 10. Frontend-Architektur

- **State**: Zustand-Stores mit **selektiven** Subscriptions (Lehre aus AUDIT:
  keine Voll-Destrukturierung → keine Re-Render-Kaskaden).
- **Timeline**: Canvas-gerendert + Virtualisierung (skaliert auf Stunden).
- **Preview**: EDL-aware — spielt den kompilierten Schnitt, nicht die Rohquelle;
  MG-Overlays via `@remotion/player` über dem `<video>`/Canvas.
- **Transkript-Panel** ⇄ Timeline bidirektional über `word_ids`.
- **API-Client**: typisiert gegen `shared/types.ts`.

## 11. Sicherheit & Robustheit (Lehren aus AUDIT.md)

- Uploads **streamen auf Disk** (kein Voll-Buffer im RAM).
- ffmpeg-Argumente als **Argv-Liste** (kein Shell-String) → keine Injection;
  drawtext/Text wird escaped.
- Alle Subprozesse async → Event-Loop bleibt frei.
- Jeder Edit persistiert + Autosave (1,5 s Debounce) + Revisionen.
- React Error-Boundaries; Job-Cleanup von Temp-Dateien.

## 12. Teststrategie

- Backend: pytest-asyncio — EDL-Compiler (Snap/Anti-Chop), Beat-Detector,
  Routing-Fallback, Tool-Registry, Export-Argv-Builder.
- Frontend: Vitest — Stores, Text↔Timeline-Sync, Timeline-Geometrie.
- Remotion: Komposition-Smoke-Tests (props → keine Render-Fehler).
