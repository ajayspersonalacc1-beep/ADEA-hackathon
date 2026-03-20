import type {
  AgentDurationPoint,
  MetricPoint,
  PipelineDetails,
  PipelineStep,
  PipelineSummary
} from "@/lib/types";

export function formatStatus(status: string) {
  return status.replaceAll("_", " ");
}

export function formatTimestamp(value: number | null | undefined) {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value * 1000));
}

export function computeDurationSeconds(
  startedAt: number | null | undefined,
  finishedAt: number | null | undefined
) {
  if (!startedAt || !finishedAt || finishedAt < startedAt) {
    return 0;
  }

  return Number((finishedAt - startedAt).toFixed(2));
}

export function deriveStepsCount(details?: Pick<PipelineDetails, "pipeline_plan">) {
  const steps = details?.pipeline_plan?.steps;
  return Array.isArray(steps) ? steps.length : 0;
}

export function deriveFailuresCount(logs: string[]) {
  return logs.filter((log) =>
    log.toLowerCase().includes("pipeline execution failed")
  ).length;
}

export function deriveAgentDurations(logs: string[]): AgentDurationPoint[] {
  const buckets = new Map<string, number>();

  for (const log of logs) {
    const match = log.match(/\[([A-Z]+)\].*?(\d+(?:\.\d+)?)s/i);
    if (!match) {
      continue;
    }

    buckets.set(match[1], (buckets.get(match[1]) ?? 0) + Number(match[2]));
  }

  return Array.from(buckets.entries()).map(([agent, duration]) => ({
    agent,
    duration: Number(duration.toFixed(2))
  }));
}

export function buildMetrics(history: PipelineSummary[]): MetricPoint[] {
  return history.slice(0, 8).reverse().map((pipeline) => ({
    label: pipeline.pipeline_id.slice(-4).toUpperCase(),
    executionTime: computeDurationSeconds(
      pipeline.started_at,
      pipeline.finished_at
    ),
    failures:
      typeof pipeline.diagnosis?.root_cause === "string" &&
      pipeline.diagnosis.root_cause
        ? 1
        : 0,
    optimizations: Array.isArray(pipeline.optimization?.recommendations)
      ? pipeline.optimization.recommendations.length
      : 0
  }));
}

export function getOptimizationRecommendations(details?: PipelineDetails) {
  const recommendations = details?.optimization?.recommendations;
  return Array.isArray(recommendations)
    ? recommendations.filter((item): item is string => typeof item === "string")
    : [];
}

export function buildLineageGraph(steps: PipelineStep[]) {
  const edges: Array<{ id: string; source: string; target: string }> = [];
  const seen = new Set<string>();

  for (const step of steps) {
    const query = step.query?.toLowerCase?.() ?? "";
    const targetMatch =
      query.match(/create\s+(?:or\s+replace\s+)?table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)/) ??
      query.match(/insert\s+into\s+([a-z_][a-z0-9_]*)/);

    if (!targetMatch) {
      continue;
    }

    const target = targetMatch[1];
    const sourceMatches = [
      ...query.matchAll(/from\s+([a-z_][a-z0-9_]*)/g),
      ...query.matchAll(/join\s+([a-z_][a-z0-9_]*)/g)
    ];

    for (const match of sourceMatches) {
      const source = match[1];
      const edgeId = `${source}-${target}`;
      if (source === target || seen.has(edgeId)) {
        continue;
      }
      seen.add(edgeId);
      edges.push({ id: edgeId, source, target });
    }
  }

  const nodes = Array.from(
    new Set(edges.flatMap((edge) => [edge.source, edge.target]))
  ).map((nodeId, index) => ({
    id: nodeId,
    position: {
      x: 60 + (index % 3) * 220,
      y: 40 + Math.floor(index / 3) * 120
    },
    data: {
      label: nodeId
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")
    }
  }));

  return { nodes, edges };
}

export function buildPipelineReport(details?: PipelineDetails) {
  if (!details) {
    return "";
  }

  return [
    "ADEA PIPELINE REPORT",
    "====================",
    `Pipeline ID: ${details.pipeline_id}`,
    `Prompt: ${details.user_prompt}`,
    `Status: ${String(details.status).toUpperCase()}`,
    `Started: ${formatTimestamp(details.started_at)}`,
    `Finished: ${formatTimestamp(details.finished_at)}`,
    "",
    "Diagnosis",
    JSON.stringify(details.diagnosis, null, 2),
    "",
    "Repair",
    JSON.stringify(details.repair_action, null, 2),
    "",
    "Optimization",
    JSON.stringify(details.optimization, null, 2),
    "",
    "Logs",
    details.logs.join("\n")
  ].join("\n");
}
