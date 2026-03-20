"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { AlertCircle, BarChart2, Database, Network, RefreshCcw } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { useAdeaDashboard } from "@/hooks/use-adea-dashboard";
import {
  buildLineageGraph,
  buildMetrics,
  buildPipelineReport,
  computeDurationSeconds,
  deriveAgentDurations,
  deriveFailuresCount,
  deriveStepsCount,
  formatTimestamp
} from "@/lib/pipeline-utils";
import type { AgentExecutionStatus } from "@/lib/types";

import { AgentExecutionTimeline } from "./components/AgentExecutionTimeline";
import { ArtifactViewer } from "./components/ArtifactViewer";
import { OptimizationPanel } from "./components/OptimizationPanel";
import { PipelineCard } from "./components/PipelineCard";
import { PipelineHistoryTable } from "./components/PipelineHistoryTable";
import { PromptInput } from "./components/PromptInput";
import { StatusBadge } from "./components/StatusBadge";

const PipelineGraph = dynamic(
  () => import("./components/PipelineGraph").then((mod) => mod.PipelineGraph),
  {
    ssr: false,
    loading: () => (
      <div className="glass-panel flex h-[468px] items-center justify-center text-sm text-muted-foreground">
        Loading pipeline graph...
      </div>
    )
  }
);

const MetricsPanel = dynamic(
  () => import("./components/MetricsPanel").then((mod) => mod.MetricsPanel),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="glass-panel h-[384px] animate-pulse" />
        <div className="glass-panel h-[384px] animate-pulse" />
      </div>
    )
  }
);

const ExecutionLogs = dynamic(
  () => import("./components/ExecutionLogs").then((mod) => mod.ExecutionLogs),
  {
    ssr: false,
    loading: () => (
      <div className="glass-panel flex h-[468px] items-center justify-center text-sm text-muted-foreground">
        Loading execution logs...
      </div>
    )
  }
);

const DEFAULT_AGENT_TIMELINE: AgentExecutionStatus[] = [
  { name: "Planner", status: "waiting", execution_time: null },
  { name: "Executor", status: "waiting", execution_time: null },
  { name: "Monitor", status: "waiting", execution_time: null },
  { name: "SchemaDiscovery", status: "waiting", execution_time: null },
  { name: "Diagnosis", status: "waiting", execution_time: null },
  { name: "Repair", status: "waiting", execution_time: null },
  { name: "Optimization", status: "waiting", execution_time: null }
];

type WorkspaceView = "topology" | "logs" | "metrics";

export default function DashboardPage() {
  const {
    history,
    activePipeline,
    activePipelineId,
    executionStatus,
    isLoading,
    isSubmitting,
    error,
    createPipeline,
    refreshHistory,
    selectPipeline
  } = useAdeaDashboard();
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("topology");

  const graph = useMemo(
    () => buildLineageGraph(activePipeline?.pipeline_plan.steps ?? []),
    [activePipeline?.pipeline_plan.steps]
  );
  const metrics = useMemo(() => buildMetrics(history), [history]);
  const durations = useMemo(
    () => deriveAgentDurations(activePipeline?.logs ?? []),
    [activePipeline?.logs]
  );
  const report = useMemo(
    () => buildPipelineReport(activePipeline ?? undefined),
    [activePipeline]
  );
  const recommendations = useMemo(
    () =>
      Array.isArray(activePipeline?.optimization?.recommendations)
        ? (activePipeline?.optimization?.recommendations as string[])
        : [],
    [activePipeline?.optimization?.recommendations]
  );
  const agentTimeline = useMemo(
    () => executionStatus?.agents ?? DEFAULT_AGENT_TIMELINE,
    [executionStatus?.agents]
  );
  const liveProgress = executionStatus?.progress ?? 0;
  const currentAgentName = useMemo(
    () =>
      executionStatus?.agents.find(
        (agent: AgentExecutionStatus) => agent.status === "running"
      )?.name ??
      executionStatus?.agents.find(
        (agent: AgentExecutionStatus) => agent.status === "failed"
      )?.name ??
      null,
    [executionStatus?.agents]
  );

  return (
    <AppShell
      headerContent={
        <Button variant="secondary" onClick={() => void refreshHistory()}>
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </Button>
      }
    >
      <div className="space-y-6">
        <PromptInput onSubmit={createPipeline} loading={isSubmitting} />

        {error ? (
          <div className="glass-panel flex items-start gap-3 border border-error/30 px-5 py-4 text-error">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <div>
              <p className="font-medium">Dashboard error</p>
              <p className="text-sm text-error/80">{error}</p>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <PipelineCard
            title="Pipeline Status"
            value={activePipeline ? String(activePipeline.status).toUpperCase() : "IDLE"}
            hint={
              activePipeline ? activePipeline.pipeline_id : "Create or select a pipeline run"
            }
            icon="status"
            accent={
              activePipeline?.status === "success"
                ? "success"
                : activePipeline?.status === "failed"
                  ? "error"
                  : "primary"
            }
          />
          <PipelineCard
            title="Execution Time"
            value={
              activePipeline
                ? `${computeDurationSeconds(activePipeline.started_at, activePipeline.finished_at)}s`
                : "--"
            }
            hint={activePipeline ? formatTimestamp(activePipeline.finished_at) : "No active run"}
            icon="duration"
            accent="primary"
          />
          <PipelineCard
            title="Steps Executed"
            value={activePipeline ? deriveStepsCount(activePipeline) : 0}
            hint="SQL steps currently in the pipeline plan"
            icon="steps"
            accent="warning"
          />
          <PipelineCard
            title="Failures Detected"
            value={activePipeline ? deriveFailuresCount(activePipeline.logs) : 0}
            hint="Monitor + repair loop anomaly count"
            icon="failures"
            accent="error"
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-4">
            <div className="glass-panel flex flex-wrap gap-2 p-2">
              <Button
                variant={workspaceView === "topology" ? "default" : "secondary"}
                onClick={() => setWorkspaceView("topology")}
              >
                Topology
              </Button>
              <Button
                variant={workspaceView === "logs" ? "default" : "secondary"}
                onClick={() => setWorkspaceView("logs")}
              >
                Logs
              </Button>
              <Button
                variant={workspaceView === "metrics" ? "default" : "secondary"}
                onClick={() => setWorkspaceView("metrics")}
              >
                Metrics
              </Button>
            </div>
            {workspaceView === "topology" ? (
              <PipelineGraph nodes={graph.nodes} edges={graph.edges} />
            ) : null}
            {workspaceView === "logs" ? (
              <ExecutionLogs
                logs={activePipeline?.logs ?? []}
                currentAgent={currentAgentName}
              />
            ) : null}
            {workspaceView === "metrics" ? (
              <MetricsPanel metrics={metrics} agentDurations={durations} />
            ) : null}
          </div>
          <div className="space-y-6">
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3">
                <Database className="h-5 w-5 text-primary" />
                <div>
                  <p className="panel-header">Active Pipeline</p>
                  <p className="mt-2 text-xl font-semibold">
                    {activePipeline?.pipeline_id ?? "No pipeline selected"}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                {activePipeline ? (
                  <>
                    <StatusBadge status={String(activePipeline.status)} />
                    <div className="rounded-full bg-muted px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                      {activePipeline.pipeline_plan.steps?.length ?? 0} steps
                    </div>
                  </>
                ) : null}
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                {activePipeline?.user_prompt ??
                  "Select a history row or run a prompt to populate dashboard details."}
              </p>
            </div>
            <AgentExecutionTimeline agents={agentTimeline} progress={liveProgress} />
            <OptimizationPanel recommendations={recommendations} />
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3">
                <Network className="h-5 w-5 text-primary" />
                <div>
                  <p className="panel-header">Run Snapshot</p>
                  <p className="mt-2 text-lg font-semibold">Current selection</p>
                </div>
              </div>
              <div className="mt-5 space-y-3 text-sm">
                <div className="flex items-center justify-between rounded-xl bg-background/40 px-4 py-3">
                  <span className="text-muted-foreground">Prompt</span>
                  <span className="max-w-[60%] truncate font-medium">
                    {activePipeline?.user_prompt ?? "Unavailable"}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-background/40 px-4 py-3">
                  <span className="text-muted-foreground">Started</span>
                  <span className="font-medium">
                    {formatTimestamp(activePipeline?.started_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-background/40 px-4 py-3">
                  <span className="text-muted-foreground">Finished</span>
                  <span className="font-medium">
                    {formatTimestamp(activePipeline?.finished_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <PipelineHistoryTable
          history={history}
          activePipelineId={activePipelineId}
          onSelect={(pipelineId) => void selectPipeline(pipelineId)}
        />

        <ArtifactViewer
          pipelineId={activePipeline?.pipeline_id ?? "pipeline"}
          report={report}
          logs={activePipeline?.logs ?? []}
        />

        <div className="glass-panel flex items-center justify-between px-5 py-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-3">
            <BarChart2 className="h-4 w-4 text-primary" />
            SWR refreshes history every 15 seconds, details every 4 seconds, and live
            execution every 1 second.
          </div>
          <div>{isLoading ? "Refreshing..." : `${history.length} pipeline runs loaded`}</div>
        </div>
      </div>
    </AppShell>
  );
}
