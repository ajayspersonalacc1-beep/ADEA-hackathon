"use client";

import { motion } from "framer-motion";
import {
  Bot,
  CheckCircle2,
  Circle,
  LoaderCircle,
  Radar,
  SearchCheck,
  ShieldAlert,
  Sparkles,
  Wrench,
  XCircle
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import type { AgentExecutionState, AgentExecutionStatus } from "@/lib/types";

const AGENT_ICONS = {
  Planner: Bot,
  Executor: Sparkles,
  Monitor: Radar,
  SchemaDiscovery: SearchCheck,
  Diagnosis: ShieldAlert,
  Repair: Wrench,
  Optimization: Sparkles
} as const;

function StatusGlyph({ status }: { status: AgentExecutionState }) {
  if (status === "completed") {
    return <CheckCircle2 className="h-5 w-5 text-success" />;
  }

  if (status === "failed") {
    return <XCircle className="h-5 w-5 text-error" />;
  }

  if (status === "running") {
    return (
      <motion.div
        animate={{ scale: [1, 1.08, 1] }}
        transition={{ duration: 1.1, repeat: Number.POSITIVE_INFINITY }}
      >
        <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
      </motion.div>
    );
  }

  return <Circle className="h-4 w-4 fill-muted text-muted-foreground" />;
}

export function AgentExecutionTimeline({
  agents,
  progress
}: {
  agents: AgentExecutionStatus[];
  progress: number;
}) {
  const lastCompletedAgent = [...agents]
    .reverse()
    .find((agent) => agent.status === "completed");
  const currentAgent =
    agents.find((agent) => agent.status === "running") ??
    agents.find((agent) => agent.status === "failed") ??
    lastCompletedAgent ??
    null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Agent Execution</CardTitle>
        <CardDescription>
          Real-time pipeline workflow across planning, execution, monitoring,
          diagnosis, repair, and optimization.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="panel-header">Current live status</p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {currentAgent?.name ?? "Awaiting pipeline activity"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Agent state</p>
              <p className="text-sm font-semibold capitalize text-primary">
                {currentAgent?.status ?? "waiting"}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="panel-header">Pipeline progress</span>
            <span className="font-medium text-foreground">{progress}%</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            />
          </div>
        </div>

        <div className="space-y-3">
          {agents.map((agent, index) => {
            const AgentIcon =
              AGENT_ICONS[agent.name as keyof typeof AGENT_ICONS] ?? Bot;

            return (
              <motion.div
                key={agent.name}
                layout
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.04 }}
                className="relative rounded-2xl border border-border bg-background/50 px-4 py-3"
              >
                {index < agents.length - 1 ? (
                  <div className="absolute left-[22px] top-[56px] h-8 w-px bg-border" />
                ) : null}
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-primary/10 p-2 text-primary">
                      <AgentIcon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{agent.name}</p>
                        <StatusGlyph status={agent.status} />
                      </div>
                      <p className="text-sm capitalize text-muted-foreground">
                        {agent.status}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <p className="text-muted-foreground">Execution time</p>
                    <p className="font-medium text-foreground">
                      {agent.execution_time ?? "--"}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
