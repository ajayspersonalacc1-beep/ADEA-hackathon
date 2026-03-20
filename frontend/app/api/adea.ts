import type {
  PipelineDetails,
  PipelineExecutionStatusResponse,
  PipelineListResponse,
  RunPipelineResponse
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_ADEA_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `ADEA API request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function runPipeline(input: {
  pipelineId: string;
  userPrompt: string;
}) {
  return request<RunPipelineResponse>("/api/run_pipeline", {
    method: "POST",
    body: JSON.stringify({
      pipeline_id: input.pipelineId,
      user_prompt: input.userPrompt
    })
  });
}

export async function getPipelineStatus(pipelineId: string) {
  return request<PipelineDetails>(`/api/v1/pipelines/status/${pipelineId}`);
}

export async function getPipelineExecutionStatus(pipelineId: string) {
  return request<PipelineExecutionStatusResponse>(
    `/api/pipeline_status/${pipelineId}`
  );
}

export async function listPipelines() {
  return request<PipelineListResponse>("/api/v1/pipelines/list");
}
