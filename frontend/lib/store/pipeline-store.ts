"use client";

import { create } from "zustand";

import { runPipeline } from "@/app/api/adea";

interface PipelineStoreState {
  activePipelineId: string | null;
  isSubmitting: boolean;
  error: string | null;
  selectPipeline: (pipelineId: string) => void;
  clearError: () => void;
  createPipeline: (prompt: string) => Promise<string | null>;
}

function createPipelineId() {
  return `web_${Date.now().toString(36)}`;
}

export const usePipelineStore = create<PipelineStoreState>((set) => ({
  activePipelineId: null,
  isSubmitting: false,
  error: null,
  selectPipeline: (pipelineId) => {
    set({ activePipelineId: pipelineId, error: null });
  },
  clearError: () => {
    set({ error: null });
  },
  createPipeline: async (prompt) => {
    const pipelineId = createPipelineId();
    set({ isSubmitting: true, error: null });

    try {
      const response = await runPipeline({ pipelineId, userPrompt: prompt });
      set({
        activePipelineId: response.pipeline_id,
        isSubmitting: false
      });
      return response.pipeline_id;
    } catch (error) {
      set({
        isSubmitting: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to create pipeline."
      });
      return null;
    }
  }
}));
