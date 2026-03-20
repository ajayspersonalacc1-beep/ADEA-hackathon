"use client";

import { memo, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { formatTimestamp } from "@/lib/pipeline-utils";
import type { PipelineSummary } from "@/lib/types";

import { StatusBadge } from "./StatusBadge";

const PAGE_SIZE = 8;

export const PipelineHistoryTable = memo(function PipelineHistoryTable({
  history,
  activePipelineId,
  onSelect
}: {
  history: PipelineSummary[];
  activePipelineId: string | null;
  onSelect: (pipelineId: string) => void;
}) {
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(history.length / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const pageItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return history.slice(start, start + PAGE_SIZE);
  }, [history, page]);

  return (
    <div id="history" className="glass-panel overflow-hidden">
      <div className="border-b border-border px-6 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Pipeline History</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Paginated run history to keep row rendering light and responsive.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <div className="rounded-full bg-muted px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
              Page {page} / {totalPages}
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Pipeline ID</TableHead>
            <TableHead>Prompt</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created At</TableHead>
            <TableHead>Execution Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageItems.map((pipeline) => (
            <TableRow
              key={pipeline.pipeline_id}
              className={
                activePipelineId === pipeline.pipeline_id ? "bg-primary/10" : ""
              }
              onClick={() => onSelect(pipeline.pipeline_id)}
            >
              <TableCell className="font-medium">{pipeline.pipeline_id}</TableCell>
              <TableCell className="max-w-[340px] truncate">
                {pipeline.user_prompt}
              </TableCell>
              <TableCell>
                <StatusBadge status={String(pipeline.status)} />
              </TableCell>
              <TableCell>{formatTimestamp(pipeline.started_at)}</TableCell>
              <TableCell>
                {pipeline.started_at && pipeline.finished_at
                  ? `${(pipeline.finished_at - pipeline.started_at).toFixed(2)}s`
                  : "Pending"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
});
