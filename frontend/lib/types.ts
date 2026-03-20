export type PipelineStatus =
  | "pending"
  | "running"
  | "failed"
  | "anomaly_detected"
  | "diagnosed"
  | "repaired"
  | "success"
  | "unrecoverable";

export interface PipelineStep {
  type: string;
  query: string;
}

export interface PipelinePlan {
  steps?: PipelineStep[];
  [key: string]: unknown;
}

export interface PipelineDetails {
  pipeline_id: string;
  user_prompt: string;
  status: PipelineStatus | string;
  pipeline_plan: PipelinePlan;
  diagnosis: Record<string, unknown>;
  repair_action: Record<string, unknown>;
  optimization: Record<string, unknown>;
  logs: string[];
  started_at: number | null;
  finished_at: number | null;
}

export interface PipelineSummary {
  pipeline_id: string;
  user_prompt: string;
  status: PipelineStatus | string;
  started_at: number | null;
  finished_at: number | null;
  diagnosis: Record<string, unknown>;
  repair_action: Record<string, unknown>;
  optimization: Record<string, unknown>;
}

export interface PipelineListResponse {
  pipelines: PipelineSummary[];
}

export interface RunPipelineResponse {
  pipeline_id: string;
  status: string;
}

export type AgentExecutionState =
  | "waiting"
  | "running"
  | "completed"
  | "failed";

export interface AgentExecutionStatus {
  name: string;
  status: AgentExecutionState;
  execution_time: string | null;
}

export interface PipelineExecutionStatusResponse {
  pipeline_id: string;
  status: string;
  progress: number;
  agents: AgentExecutionStatus[];
}

export interface MetricPoint {
  label: string;
  executionTime: number;
  failures: number;
  optimizations: number;
}

export interface AgentDurationPoint {
  agent: string;
  duration: number;
}
