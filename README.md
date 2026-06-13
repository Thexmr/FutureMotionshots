# Motionshot Studio

> **Das KI-Videostudio.** Textbasiert schneiden wie in Descript — aber mit
> Profi-NLE-Unterbau, einem *sehenden* KI-Agenten und automatischen Motion
> Graphics über Remotion, Hyperframes und HeyGen. Lokal-first, freie Modellwahl.

Motionshot übernimmt Descripts einfachen Grundgedanken (importieren →
transkribieren → über Text schneiden → Canvas/Timeline → KI-Befehle →
verbessern → exportieren) und erweitert ihn um genau die Bereiche, in denen
Descript schwach ist: **Speed Ramps, Beat-Cutting, Multicam-Musikvideo-Schnitt,
Keyframe-Effekte, Motion Graphics und einen Agenten mit visueller
Selbstkontrolle** — ohne Cloud-Zwang.

Dies ist **kein** Descript-Klon: kein kopiertes Layout, keine Assets/Texte/Marken.
Eigenständige Premium-UI, eigene Architektur, deutlich mehr Funktionen.

---

## Was schon läuft (verifiziert)

- **Datenmodell** mit nativen Speed Ramps, Beatgrid, Multicam, Keyframe-Effekten
  und Transkript↔Clip-Verknüpfung (`shared/types.ts` ⇄ `backend/app/models`).
- **Textbasiertes Schneiden**: EDL-Compiler mit Word-Boundary-Snapping +
  Anti-Chop (`backend/app/services/edl_compiler.py`).
- **Beat-Detection** (lokal, numpy) für Musikvideo-Schnitt — erkennt BPM/Beats/
  Downbeats/Energie (`beat_detector.py`).
- **KI-Agent** mit echtem Tool-Calling auf dem Timeline-Modell + **visueller
  Selbstprüfung** (Frames → Vision-Modell → Score → Retry) und Checkpoints
  (`backend/app/agent/`).
- **Multi-Provider-Client** (Anthropic / OpenAI-kompatibel / Ollama) + **aufgaben-
  basiertes Modell-Routing** mit Fallback, BYO-Key (`ai_client.py`,
  `settings_store.py`).
- **Premium-Frontend** (React 18 + Vite + Tailwind v4): 3-Spalten-Editor
  (Transkript · Canvas · Director) + Canvas-Timeline mit Beatgrid-Lineal,
  Settings/Provider-Panel. Baut sauber durch (`npm run build`).
- **Remotion-Templates**: Lower-Third, Kinetic-Captions, Title-Card +
  PNG-Sequenz-Renderer für die ffmpeg-Composite-Pipeline.
- **8 grüne Backend-Tests** für EDL, Beats, Routing, Agent-Tools.

Siehe `docs/` für den vollständigen **Benchmark-Bericht** gegen Descript,
das **Produktkonzept**, die **Architektur** und das **UI-Design**.

---

## Schnellstart

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # + optional: pip install faster-whisper
uvicorn app.main:app --reload --port 8787

# Frontend (Dev mit Hot-Reload)
cd frontend && npm install && npm run dev # → http://localhost:5173

# Produktion (Single-Port: Backend servt das gebaute Frontend auf :8787)
cd frontend && npm run build
```

Lokal-first: ohne jeden Cloud-Key lauffähig, sobald `faster-whisper` (Transkript)
und `ollama` (KI-Agent) installiert sind. Cloud-Provider sind optional und
per Aufgabe routbar.

```bash
npm run dev   # startet Backend + Frontend zusammen (siehe package.json)
```

---

## Architektur (Kurzform)

```
shared/types.ts     Vertrag (Frontend ⇄ Backend ⇄ Remotion)
backend/            FastAPI — Modelle, EDL-Compiler, Beats, Agent, Render, Routing
frontend/           React + Vite + Tailwind — Premium-Editor (Canvas-Timeline)
remotion/           Datengetriebene Motion-Graphics-Templates (Remotion 4)
docs/               Benchmark · Konzept · Architektur · UI-Design
```

Details: [`docs/03-architecture.md`](docs/03-architecture.md).

---

## Roadmap (nächste Schritte)

- EDL-aware Echtzeit-Preview (kompilierter Schnitt statt Rohquelle) inkl.
  Remotion-`<Player>`-Overlay-Layer.
- Vollständige Async-Export-Pipeline (Per-Segment-Render → Concat → Encode) mit
  echtem Fortschritt + Cancel.
- Drag/Trim/Split-Interaktionen auf der Canvas-Timeline + Inspector-Editing.
- HeyGen-Avatar-Workflow und Hyperframes-HTML/CSS-Renderer anbinden.
- Multicam-Beat-Switching und Speed-Ramp-Presets im UI.

> Lizenzhinweis: Remotion benötigt ab gewisser Unternehmensgröße eine
> kommerzielle Lizenz. Vor kommerziellem Launch prüfen.
