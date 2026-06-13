import type {
  Project,
  Timeline,
  Transcript,
  BeatGrid,
  StudioSettings,
} from "@shared/types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  capabilities: () =>
    req<{ ffmpeg: boolean; whisper: boolean; providers: string[] }>("/capabilities"),

  listProjects: () => req<Project[]>("/projects"),
  createProject: (name: string, aspect: string) =>
    req<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, aspect }),
    }),
  getProject: (id: string) => req<Project>(`/projects/${id}`),
  deleteProject: (id: string) =>
    req<{ deleted: boolean }>(`/projects/${id}`, { method: "DELETE" }),

  saveTimeline: (id: string, timeline: Timeline) =>
    req<{ revision: number; duration: number }>(`/projects/${id}/timeline`, {
      method: "PATCH",
      body: JSON.stringify(timeline),
    }),

  uploadMedia: async (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/projects/${id}/media`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  transcribe: (id: string, mediaId: string) =>
    req<{ transcript: Transcript; clips: number }>(
      `/projects/${id}/media/${mediaId}/transcribe`,
      { method: "POST" },
    ),

  getTranscript: (tid: string) => req<Transcript>(`/transcripts/${tid}`),

  recompile: (id: string, transcriptId: string, words: { id: string; state: string }[]) =>
    req<{ clips: number; duration: number }>(`/projects/${id}/recompile`, {
      method: "POST",
      body: JSON.stringify({ transcript_id: transcriptId, words }),
    }),

  analyseBeats: (id: string, mediaId: string) =>
    req<BeatGrid>(`/projects/${id}/media/${mediaId}/beats`, { method: "POST" }),

  runAgent: (id: string, message: string) =>
    req<{ checkpoints: number; revision: number }>(`/projects/${id}/agent`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  export: (id: string, settings: Record<string, unknown>) =>
    req<{ started: boolean }>(`/projects/${id}/export`, {
      method: "POST",
      body: JSON.stringify(settings),
    }),

  getSettings: () => req<StudioSettings>("/settings"),
  saveSettings: (s: StudioSettings) =>
    req<{ ok: boolean }>("/settings", { method: "PUT", body: JSON.stringify(s) }),
  testProvider: (providerId: string) =>
    req<{ status: string; detail: string }>(
      `/settings/providers/${providerId}/test`,
      { method: "POST" },
    ),
};
