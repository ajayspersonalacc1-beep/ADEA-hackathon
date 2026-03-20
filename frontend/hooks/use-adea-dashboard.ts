"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { useShallow } from "zustand/react/shallow";

import {
  getPipelineExecutionStatus,
  getPipelineStatus,
  listPipelines
} from "@/app/api/adea";
import { usePipelineStore } from "@/lib/store/pipeline-store";

export function useAdeaDashboard() {
  const {
    activePipelineId,
    isSubmitting,
    error,
    selectPipeline,
    clearError,
    createPipeline: createPipelineAction
  } = usePipelineStore(
    useShallow((state) => ({
      activePipelineId: state.activePipelineId,
      isSubmitting: state.isSubmitting,
      error: state.error,
      selectPipeline: state.selectPipeline,
      clearError: state.clearError,
      createPipeline: state.createPipeline
    }))
  );

  const { mutate } = useSWRConfig();
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const syncVisibility = () => {
      setIsVisible(document.visibilityState === "visible");
    };

    syncVisibility();
    document.addEventListener("visibilitychange", syncVisibility);

    return () => document.removeEventListener("visibilitychange", syncVisibility);
  }, []);

  const {
    data: historyData,
    isLoading: isHistoryLoading,
    mutate: mutateHistory
  } = useSWR("pipeline-history", listPipelines, {
    refreshInterval: isVisible ? 15000 : 0,
    dedupingInterval: 5000,
    revalidateOnFocus: true,
    keepPreviousData: true
  });

  const history = useMemo(() => {
    return [...(historyData?.pipelines ?? [])].sort((a, b) => {
      const aTime = a.started_at ?? 0;
      const bTime = b.started_at ?? 0;
      return bTime - aTime;
    });
  }, [historyData?.pipelines]);

  useEffect(() => {
    if (!activePipelineId && history[0]?.pipeline_id) {
      selectPipeline(history[0].pipeline_id);
    }
  }, [activePipelineId, history, selectPipeline]);

  const {
    data: activePipeline,
    isLoading: isPipelineLoading,
    mutate: mutateActivePipeline
  } = useSWR(
    activePipelineId ? ["pipeline-details", activePipelineId] : null,
    ([, pipelineId]) => getPipelineStatus(pipelineId),
    {
      refreshInterval: (data) => {
        if (!isVisible) {
          return 0;
        }

        const status = String(data?.status ?? "").toLowerCase();
        return ["success", "failed", "unrecoverable"].includes(status) ? 0 : 4000;
      },
      dedupingInterval: 1500,
      revalidateOnFocus: true,
      keepPreviousData: true
    }
  );

  const {
    data: executionStatus,
    mutate: mutateExecutionStatus
  } = useSWR(
    activePipelineId ? ["pipeline-execution", activePipelineId] : null,
    ([, pipelineId]) => getPipelineExecutionStatus(pipelineId),
    {
      refreshInterval: (data) => {
        if (!isVisible) {
          return 0;
        }

        const status = String(data?.status ?? "").toLowerCase();
        return ["success", "failed", "unrecoverable"].includes(status) ? 0 : 1000;
      },
      dedupingInterval: 500,
      revalidateOnFocus: true,
      keepPreviousData: true
    }
  );

  const currentStatus = String(
    executionStatus?.status ?? activePipeline?.status ?? ""
  ).toLowerCase();
  const isTerminal = ["success", "failed", "unrecoverable"].includes(currentStatus);

  useEffect(() => {
    if (!activePipelineId || !isTerminal) {
      return;
    }

    void Promise.all([mutateHistory(), mutateActivePipeline()]);
  }, [activePipelineId, isTerminal, mutateActivePipeline, mutateHistory]);

  const refreshHistory = useCallback(async () => {
    clearError();
    await mutateHistory();
  }, [clearError, mutateHistory]);

  const createPipeline = useCallback(
    async (prompt: string) => {
      clearError();
      const pipelineId = await createPipelineAction(prompt);
      if (!pipelineId) {
        return;
      }

      await Promise.all([
        mutate("pipeline-history"),
        mutate(["pipeline-details", pipelineId]),
        mutate(["pipeline-execution", pipelineId])
      ]);
    },
    [clearError, createPipelineAction, mutate]
  );

  const isLoading =
    isHistoryLoading || (Boolean(activePipelineId) && isPipelineLoading);

  return {
    history,
    activePipelineId,
    activePipeline: activePipeline ?? null,
    executionStatus: executionStatus ?? null,
    isLoading,
    isSubmitting,
    error,
    refreshHistory,
    selectPipeline: async (pipelineId: string) => {
      clearError();
      selectPipeline(pipelineId);
      await Promise.all([
        mutate(["pipeline-details", pipelineId]),
        mutate(["pipeline-execution", pipelineId])
      ]);
    },
    createPipeline,
    refreshActivePipelineDetails: mutateActivePipeline,
    pollActiveExecution: mutateExecutionStatus
  };
}
