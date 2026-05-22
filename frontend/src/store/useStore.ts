import { create } from "zustand";
import type { SourceDoc } from "@/lib/api";

export interface IngestionJob {
  id: string;
  filename: string;
  collection: string;
  status: "uploading" | "pending" | "done" | "error";
  error?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDoc[];
  isStreaming?: boolean;
  queryLogId?: string;
  feedback?: 1 | -1 | null;
}

interface AppState {
  collection: string;
  setCollection: (c: string) => void;

  messages: Message[];
  addMessage: (msg: Message) => void;
  updateMessage: (id: string, patch: Partial<Message>) => void;
  appendToken: (id: string, token: string) => void;
  clearMessages: () => void;

  ingestionJobs: IngestionJob[];
  addIngestionJob: (job: IngestionJob) => void;
  updateIngestionJob: (id: string, patch: Partial<IngestionJob>) => void;
}

export const useStore = create<AppState>((set) => ({
  collection: "general",
  setCollection: (c) => set({ collection: c }),

  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  appendToken: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    })),
  clearMessages: () => set({ messages: [] }),

  ingestionJobs: [],
  addIngestionJob: (job) => set((s) => ({ ingestionJobs: [job, ...s.ingestionJobs] })),
  updateIngestionJob: (id, patch) =>
    set((s) => ({
      ingestionJobs: s.ingestionJobs.map((j) => (j.id === id ? { ...j, ...patch } : j)),
    })),
}));
