# Produktkonzept: Motionshot Studio

> **Das KI-Videostudio.** Textbasiert schneiden wie in Descript — aber mit
> Profi-NLE-Unterbau, einem *sehenden* KI-Agenten und automatischen Motion
> Graphics über Remotion, Hyperframes und HeyGen. Lokal-first, freie Modellwahl.

## 1. Positionierung

Motionshot übernimmt Descripts genialen Grundgedanken — **import → transkribieren
→ über Text schneiden → Canvas/Timeline → KI-Befehle → verbessern → exportieren**
— und erweitert ihn um genau die Bereiche, in denen Descript schwach ist:
Motion Graphics, Musikvideo-Schnitt, Profi-Kontrolle, lokale KI und einen Agenten,
der sein eigenes Ergebnis visuell prüft.

Zielgruppen: Creator (Shorts/YouTube), Cutter/Editoren (Profi-Kontrolle),
Motion Designer (Templates/Keyframes), Musikvideo-Editoren (Beat/Multicam).

## 2. Leitprinzipien

1. **Text zuerst, Timeline immer.** Beide Sichten editieren dasselbe Modell und
   bleiben live synchron (Wort löschen ⇄ Clip kürzen).
2. **Der Agent hat Augen.** Jede autonome Aktion wird gegen das gerenderte Frame
   geprüft (Vision-Modell), bewertet und ggf. korrigiert.
3. **Lokal-first, Cloud optional.** faster-whisper + Ollama out-of-the-box;
   Cloud-Provider per BYO-Key, frei routbar pro Aufgabe.
4. **Determinismus vor Halluzination.** KI schlägt vor; Schnitte werden
   deterministisch auf Wortgrenzen/Beats abgebildet.
5. **Premium, aber schnell.** Eine ruhige, dunkle Pro-UI; jede Aktion < 1 Klick
   entfernt; Tastatur-first.

## 3. Kernfunktionen (MVP → Pro)

### Einfacher Kern (wie Descript, besser)
- Video/Audio importieren, automatisch transkribieren (Wort-Level).
- **Textbasiertes Schneiden**: Wörter `cut`/`kept`; EDL-Compiler erzeugt Clips
  mit Word-Boundary-Snapping + 30 ms Audio-Fades.
- Filler-/Pausen-Entfernung, Repeat-/Retake-Erkennung (Levenshtein/Alignment).
- Auto-Captions (10 Stile, Keyword-Emphasis), Studio-Audio-Enhancement.
- EDL-aware **Preview** (zeigt den Schnitt, nicht die Rohquelle) + Export.

### Pro-Editing (Descript fehlt das)
- **Speed Ramps** mit Keyframes, Bezier/Hold, Pitch-Erhalt.
- **Keyframe-Effekte**: Zoom/Pan/Shake/Blur/Color-Grade/Vignette mit Easing.
- **Auto-Zoom** (audiogetrieben) & **Smart Reframe** (Face-Tracking) für 9:16.
- Transitions: Crossfade, Whip, Zoom-Punch, Glitch, Film-Burn.

### Musikvideo-Suite (Descript fehlt komplett)
- **Beatgrid**: BPM/Beats/Downbeats/Energy aus der Musikspur.
- **Beat-Cutting**: Schnitte auf Beats snappen, Schnittdichte nach Energie.
- **Multicam**: synchronisierte Angles (`multicam_group`/`sync_offset`),
  Beat-getriebene Angle-Switches.
- Speed-Ramp-Presets („Punch-in on drop", „Time-freeze on hit").

### Motion Graphics (Automotion)
- **Remotion-Templates** (datengetrieben, React): Titel, Lower-Thirds, Callouts,
  Kinetic-Captions, Charts, Social-Frames.
- **Hyperframes**: HTML/CSS-Renderings für beliebige Designs, frame-genau geseekt.
- **HeyGen**: autonome Avatar-/Spokesperson-Videos (Script → Render → Pipeline).
- **Automotion**: der Agent platziert MG kontextbezogen (Keyword → Callout etc.).

### KI-Agent (das Herzstück)
- **Chat + Tool-Calling** auf dem Timeline-Modell (siehe `04`/`03`).
- **Visuelle Selbstprüfung**: Frames extrahieren → Vision-Modell → Score → Retry.
- **Checkpoints**: jede Aktion ist als Snapshot zurücknehmbar.
- **Autonomer Regie-Modus**: „Mach daraus einen 30-s-TikTok mit Beat-Cuts."

### Plattform & Modelle
- BYO-Key für Anthropic/OpenAI/OpenRouter/Ollama/HeyGen/ElevenLabs/Pexels/Pixabay.
- **Aufgabenbasiertes Routing**: z. B. günstiges Modell für Analyse, starkes für
  Cleanup, Vision-Modell für Selbstprüfung, lokal für Datenschutz.

## 4. Differenzierung in einem Satz

> Descript macht das **Reden** schneiden einfach. Motionshot macht das **ganze
> Video** — Schnitt, Motion, Musik, Regie — einfach *und* profi-tauglich, mit
> einem KI-Agenten, der sieht, was er tut.

## 5. Abgrenzung / Nicht-Ziele (MVP)

- Kein 1:1-Descript-Layout, keine kopierten Assets/Texte/Marken.
- Kein vollwertiges DAW; Audio bleibt „pro-genug" (Loudness, Denoise, Duck).
- Kein 3D-Compositing; Motion = 2D/2.5D über Remotion/Hyperframes.

## 6. Erfolgskriterien

- Talking-Head 10 min → sauberer Social-Cut in < 60 s (Auto-Modus).
- Musikvideo: 1 Song + 3 Angles → beat-synchroner Multicam-Cut in wenigen Klicks.
- Agent-Aktionen mit Vision-Score ≥ 0,8 ohne menschliche Korrektur in > 70 % der Fälle.
- Komplett lokal lauffähig (faster-whisper + Ollama) ohne Cloud-Key.
