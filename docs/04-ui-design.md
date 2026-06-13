# UI-Design: Motionshot Studio

Eigenständiges Premium-Interface — **nicht** von Descript kopiert. Ruhig, dunkel,
fokussiert, Tastatur-first. Inspiration: Profi-NLEs (Resolve/Premiere) +
moderne Produkt-UI, aber mit dem textbasierten Workflow als Herzstück.

## 1. Designprinzipien

1. **Eine Bühne, drei Linsen.** Transkript, Canvas und Timeline zeigen *dasselbe*
   Projekt aus drei Blickwinkeln — immer synchron.
2. **Ruhe vor Dichte.** Dunkles Neutral, eine Akzentfarbe, großzügiger Raum.
   Werkzeuge erscheinen kontextbezogen (Inspector), nicht permanent.
3. **Der Agent ist ein Panel, kein Popup.** Persistente rechte „Director"-Spalte
   mit Chat, Action-Cards und Vision-Checks.
4. **Tastatur-first.** Jede häufige Aktion hat einen Shortcut; Maus ist optional.
5. **Sichtbares Vertrauen.** Agent-Aktionen zeigen, was sie taten, mit Undo und
   Vision-Score — keine Blackbox.

## 2. Design-Tokens

```
Hintergrund   bg-base    #0B0D10   (fast schwarz, leicht blau)
Panel         bg-panel   #14171C
Erhöht        bg-elev    #1C2027
Linie         border     #272C34
Text primär   #E8EBF0
Text sekundär #9AA3B2
Akzent        accent     #6E8BFF  (Indigo-Blau) + Hover #8AA1FF
Erfolg/Beat   #3DDC97
Warnung       #FFB454
Caption-Gold  #FCD34D
Radius        12px (Panels) / 8px (Controls)
Schrift-UI    Inter
Schrift-Mono  JetBrains Mono (Timecodes)
```

## 3. Layout (Editor)

```
┌──────────────────────────────────────────────────────────────────────┐
│ TopBar:  ◀ Projekt   ·   [Auto] [Manuell] [Regie]   ·   Export ▸  ⚙   │
├───────────────┬──────────────────────────────────┬─────────────────────┤
│ TRANSCRIPT    │            CANVAS / PREVIEW        │  DIRECTOR (Agent)   │
│ (Skript)      │  EDL-aware Vorschau + MG-Overlay   │  Chat + Actions     │
│               │  ──────────────────────────────    │  + Vision-Checks    │
│ Wort-Tokens   │  Transport · Zeit · Aspect         │                     │
│ kept/cut      │                                    │  Inspector (wenn    │
│ Speaker       │                                    │  Clip selektiert)   │
├───────────────┴──────────────────────────────────┴─────────────────────┤
│ TIMELINE  (Canvas, multi-track, Beatgrid-Lineal, Playhead, Zoom)        │
│  V1 / B-Roll / Overlay / Caption / Audio / Music                        │
└──────────────────────────────────────────────────────────────────────┘
StatusBar:  Revision · Autosave · Render-Jobs · faster-whisper/Ollama-Status
```

- **Links – Transkript:** Wörter als Tokens; `cut`-Wörter durchgestrichen/gedimmt.
  Markieren + Entf schneidet; Tippen korrigiert (Audio bleibt). Speaker-Labels,
  Filler/Pausen hervorgehoben mit 1-Klick-Entfernen.
- **Mitte – Canvas:** zeigt den **kompilierten Schnitt**, nicht die Rohquelle;
  MG-Overlays live via Remotion-Player. Transport, Loop, Aspect-Umschalter.
- **Rechts – Director:** Agent-Chat; jede Aktion als Card (Tool, Args,
  Vision-Score, Undo). Wenn ein Clip selektiert ist, klappt der **Inspector**
  auf (Speed-Ramp-Kurve, Effekt-Keyframes, Transition, Overlay-Props).
- **Unten – Timeline:** Canvas-gerendert; Beatgrid als Lineal-Ticks; Clips mit
  Speed-Ramp-Kurve und Keyframe-Punkten; Snap zu Beats/Wortgrenzen.

## 4. Modi (TopBar-Umschalter)

- **Auto** — Plattform wählen → Video droppen → fertiger Schnitt (wie Descript,
  schneller). Zeigt danach editierbares Ergebnis.
- **Manuell** — volles NLE: Trim/Split/Drag, Keyframes, Speed Ramps, Multicam.
- **Regie** — Agent-getrieben: Befehl in natürlicher Sprache → Agent plant,
  führt aus, prüft visuell, zeigt Diff.

## 5. Schlüssel-Interaktionen

| Aktion | Verhalten |
|---|---|
| Wort im Skript löschen | Clip an der Stelle geschnitten (Snap+Anti-Chop), Timeline updatet live |
| Clip in Timeline trimmen | Transkript markiert betroffene Wörter als `cut` |
| Beat-Lineal anklicken | Playhead snappt auf Beat; „B" = Cut auf nächsten Beat |
| Speed-Ramp ziehen | Bezier-Kurve im Inspector; Vorschau skaliert Clip-Länge |
| „/" im Skript | Szene/Marker einfügen |
| Agent-Card „Undo" | Stellt Checkpoint vor der Aktion wieder her |

## 6. Tastatur (Auszug)

```
Space  Play/Pause      I/O  In/Out        S  Split        B  Cut-on-Beat
←/→    Frame           ⇧←/→ 1 s            J/K/L  Shuttle   Z  Zoom-Effekt
T      MG-Template     R  Speed-Ramp       M  Mute         ⌘Z Undo (Checkpoint)
G      Agent fokussieren (Director)        ⌘↵ Export
```

## 7. Motion-Graphics-Browser

Galerie mit Live-Vorschau (Remotion-Player thumbnails). Filter nach Kategorie
(Title, Lower-Third, Callout, Caption, Transition, Chart, Social). Auswahl →
Inspector mit Props-Formular (aus `props_schema`). „Automotion"-Button lässt den
Agenten passende MG entlang des Transkripts/der Beats platzieren.

## 8. Settings / Provider

Tabs: **Provider & Keys** (BYO, Test-Button mit Status-Badge) · **Routing**
(Aufgabe → Provider/Modell + Fallback) · **Transkription** (Whisper-Modell,
Sprache) · **Captions** (10 Stile) · **Audio** (Loudness-Target, Denoise) ·
**Output** (Codec, Auflösung, Hardware-Accel).

## 9. Zustände & Feedback

- Skeletons beim Transkribieren/Beatgrid; Fortschritt im StatusBar.
- Agent-Aktion: „running" (Puls) → „done" (Vision-Score-Badge) / „failed" (Grund).
- Autosave-Indikator + Revisionsnummer; Render-Job mit echtem %-Fortschritt + Cancel.
