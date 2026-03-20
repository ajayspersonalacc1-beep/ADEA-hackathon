"use client";

import { DatabaseZap, Maximize2 } from "lucide-react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node
} from "reactflow";
import "reactflow/dist/style.css";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export function PipelineGraph({
  nodes,
  edges
}: {
  nodes: Node[];
  edges: Edge[];
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Pipeline DAG</CardTitle>
          <CardDescription>
            React Flow lineage graph with pan, zoom, and dependency highlighting.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
          <Maximize2 className="h-3.5 w-3.5" />
          Zoom enabled
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[360px] overflow-hidden rounded-2xl border border-border bg-slate-950/95">
          {nodes.length ? (
            <ReactFlow fitView nodes={nodes} edges={edges}>
              <MiniMap />
              <Controls />
              <Background gap={20} size={1} color="#334155" />
            </ReactFlow>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-300">
              <DatabaseZap className="h-8 w-8" />
              <p>No lineage nodes detected for the current pipeline plan.</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
