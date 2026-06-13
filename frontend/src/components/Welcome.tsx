import { useEffect, useState } from "react";
import type { Project } from "@shared/types";
import { api } from "../api/client";

const ASPECTS = ["16:9", "9:16", "1:1", "4:5", "21:9"] as const;

export function Welcome({
  onOpen,
  onSettings,
}: {
  onOpen: (id: string) => void;
  onSettings: () => void;
}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [aspect, setAspect] = useState<string>("16:9");

  useEffect(() => {
    void api.listProjects().then(setProjects);
  }, []);

  const create = async () => {
    const p = await api.createProject(name || "Neues Projekt", aspect);
    onOpen(p.id);
  };

  return (
    <div className="flex h-full flex-col items-center justify-center gap-10 px-6">
      <header className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight">
          Motionshot <span className="text-accent">Studio</span>
        </h1>
        <p className="mt-2 max-w-lg text-ink-dim">
          Textbasiert schneiden. Mit KI Regie führen. Mit Motion Graphics veredeln.
        </p>
      </header>

      <div className="panel w-full max-w-2xl p-6">
        <div className="flex gap-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Projektname"
            className="ctl flex-1 px-4 py-3 text-ink outline-none focus:accent-glow"
          />
          <select
            value={aspect}
            onChange={(e) => setAspect(e.target.value)}
            className="ctl px-3 py-3 text-ink"
          >
            {ASPECTS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <button
            onClick={create}
            className="rounded-control bg-accent px-5 py-3 font-medium text-base text-[#0b0d10] hover:bg-accent-hi"
          >
            Erstellen
          </button>
        </div>
      </div>

      <div className="w-full max-w-2xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-ink-dim">Zuletzt bearbeitet</h2>
          <button onClick={onSettings} className="text-sm text-ink-dim hover:text-ink">
            ⚙ Einstellungen
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {projects.length === 0 && (
            <p className="col-span-2 text-sm text-ink-dim">Noch keine Projekte.</p>
          )}
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => onOpen(p.id)}
              className="panel p-4 text-left transition hover:border-[var(--color-accent)]"
            >
              <div className="font-medium">{p.name}</div>
              <div className="mt-1 text-xs text-ink-dim">
                {p.aspect} · {p.fps}fps · {p.media.length} Medien
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
