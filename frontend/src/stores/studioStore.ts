import { create } from "zustand";
import type {
  Project,
  Transcript,
  AgentMessage,
  AgentAction,
  AgentVisualCheck,
  StudioEvent,
} from "@shared/types";
import { api } from "../api/client";

export type EditorMode = "auto" | "manual" | "director";

interface StudioState {
  // project
  project: Project | null;
  transcript: Transcript | null;
  revision: number;
  mode: EditorMode;

  // playback / selection (kept here so panels stay in sync without prop drilling)
  playhead: number; // seconds
  playing: boolean;
  selectedClipId: string | null;
  zoom: number; // px per second

  // director
  messages: AgentMessage[];
  actions: AgentAction[];
  visualChecks: AgentVisualCheck[];
  agentBusy: boolean;

  // jobs
  jobProgress: { stage: string; progress: number } | null;

  // actions
  setMode: (m: EditorMode) => void;
  loadProject: (id: string) => Promise<void>;
  setPlayhead: (t: number) => void;
  setPlaying: (p: boolean) => void;
  selectClip: (id: string | null) => void;
  setZoom: (z: number) => void;
  toggleWord: (wordId: string) => Promise<void>;
  removeFillers: () => Promise<void>;
  sendAgent: (text: string) => Promise<void>;
  applyEvent: (e: StudioEvent) => void;
}

export const useStudio = create<StudioState>((set, get) => ({
  project: null,
  transcript: null,
  revision: 0,
  mode: "manual",
  playhead: 0,
  playing: false,
  selectedClipId: null,
  zoom: 90,
  messages: [],
  actions: [],
  visualChecks: [],
  agentBusy: false,
  jobProgress: null,

  setMode: (mode) => set({ mode }),

  loadProject: async (id) => {
    const project = await api.getProject(id);
    let transcript: Transcript | null = null;
    const withTranscript = project.media.find((m) => m.transcript_id);
    if (withTranscript?.transcript_id) {
      transcript = await api.getTranscript(withTranscript.transcript_id);
    }
    set({ project, transcript, revision: project.revision ?? 0 });
  },

  setPlayhead: (t) => set({ playhead: Math.max(0, t) }),
  setPlaying: (playing) => set({ playing }),
  selectClip: (id) => set({ selectedClipId: id }),
  setZoom: (z) => set({ zoom: Math.min(400, Math.max(20, z)) }),

  toggleWord: async (wordId) => {
    const { transcript, project } = get();
    if (!transcript || !project) return;
    const words = transcript.words.map((w) =>
      w.id === wordId ? { ...w, state: w.state === "cut" ? "kept" : "cut" } : w,
    );
    set({ transcript: { ...transcript, words: words as Transcript["words"] } });
    const res = await api.recompile(
      project.id,
      transcript.id,
      words.map((w) => ({ id: w.id, state: w.state })),
    );
    // Reload the recompiled timeline so the bottom panel reflects the new cut.
    await get().loadProject(project.id);
    set({ jobProgress: null });
    void res;
  },

  removeFillers: async () => {
    const { transcript, project } = get();
    if (!transcript || !project) return;
    const words = transcript.words.map((w) =>
      w.kind === "filler" ? { ...w, state: "cut" } : w,
    );
    set({ transcript: { ...transcript, words: words as Transcript["words"] } });
    await api.recompile(
      project.id,
      transcript.id,
      words.map((w) => ({ id: w.id, state: w.state })),
    );
    await get().loadProject(project.id);
  },

  sendAgent: async (text) => {
    const { project } = get();
    if (!project) return;
    set((s) => ({
      agentBusy: true,
      messages: [
        ...s.messages,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: text,
          created_at: new Date().toISOString(),
        },
      ],
    }));
    try {
      await api.runAgent(project.id, text);
      await get().loadProject(project.id);
    } finally {
      set({ agentBusy: false });
    }
  },

  applyEvent: (e) => {
    switch (e.type) {
      case "agent.message":
        set((s) => ({ messages: [...s.messages, e.message] }));
        break;
      case "agent.action":
        set((s) => ({ actions: [...s.actions.slice(-30), e.action] }));
        break;
      case "agent.visual_check":
        set((s) => ({ visualChecks: [...s.visualChecks.slice(-10), e.check] }));
        break;
      case "job.progress":
        set({ jobProgress: { stage: e.stage, progress: e.progress } });
        break;
      case "job.done":
        set({ jobProgress: { stage: "done", progress: 1 } });
        break;
      case "job.failed":
        set({ jobProgress: { stage: "failed", progress: 0 } });
        break;
      case "timeline.updated":
        set({ revision: e.revision });
        break;
    }
  },
}));
