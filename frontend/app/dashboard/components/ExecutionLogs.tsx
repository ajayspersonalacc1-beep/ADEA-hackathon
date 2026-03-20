"use client";

import { memo, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { TerminalSquare } from "lucide-react";
import {
  FixedSizeList,
  type ListChildComponentProps,
  type FixedSizeList as FixedSizeListRef
} from "react-window";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const ROW_HEIGHT = 44;
const LIST_HEIGHT = 360;

function agentTag(agentName: string | null | undefined) {
  if (!agentName) {
    return null;
  }

  if (agentName === "SchemaDiscovery") {
    return "[SCHEMA]";
  }

  return `[${agentName
    .replace("Monitor", "MONITOR")
    .replace("Planner", "PLANNER")
    .replace("Executor", "EXECUTOR")
    .replace("Diagnosis", "DIAGNOSIS")
    .replace("Repair", "REPAIR")
    .replace("Optimization", "OPTIMIZATION")}]`;
}

interface LogRowData {
  highlightedTag: string | null;
  logs: string[];
}

const LogRow = memo(function LogRow({
  index,
  style,
  data
}: ListChildComponentProps<LogRowData>) {
  const log = data.logs[index];
  const isHighlighted =
    Boolean(data.highlightedTag) && log.includes(data.highlightedTag as string);

  return (
    <div
      style={style}
      className={`border-b border-slate-800 px-2 py-2 last:border-b-0 ${
        isHighlighted ? "rounded-lg bg-primary/15 text-white" : ""
      }`}
    >
      <div className="truncate font-mono text-sm text-slate-200">
        <span className="mr-3 text-primary">
          [{String(index + 1).padStart(2, "0")}]
        </span>
        {log}
      </div>
    </div>
  );
});

export const ExecutionLogs = memo(function ExecutionLogs({
  logs,
  currentAgent
}: {
  logs: string[];
  currentAgent?: string | null;
}) {
  const [filter, setFilter] = useState("");
  const listRef = useRef<FixedSizeListRef<LogRowData> | null>(null);
  const highlightedTag = agentTag(currentAgent);
  const deferredFilter = useDeferredValue(filter);

  const filteredLogs = useMemo(() => {
    const normalized = deferredFilter.trim().toLowerCase();
    if (!normalized) {
      return logs;
    }
    return logs.filter((log) => log.toLowerCase().includes(normalized));
  }, [deferredFilter, logs]);

  const rowData = useMemo<LogRowData>(
    () => ({
      highlightedTag,
      logs: filteredLogs
    }),
    [filteredLogs, highlightedTag]
  );

  useEffect(() => {
    if (!listRef.current || !filteredLogs.length) {
      return;
    }

    listRef.current.scrollToItem(filteredLogs.length - 1, "end");
  }, [filteredLogs.length]);

  return (
    <Card id="logs">
      <CardHeader>
        <CardTitle>Execution Logs</CardTitle>
        <CardDescription>
          Virtualized terminal output with filters, active-agent highlighting, and live
          tailing.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {highlightedTag ? (
          <div className="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-primary">
            Live highlight follows {currentAgent} logs while that agent is active.
          </div>
        ) : null}
        <Input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filter by agent tag, keyword, or status"
        />
        <div className="rounded-2xl border border-border bg-slate-950 px-2 py-2">
          {filteredLogs.length ? (
            <FixedSizeList
              ref={listRef}
              height={LIST_HEIGHT}
              width="100%"
              itemCount={filteredLogs.length}
              itemData={rowData}
              itemSize={ROW_HEIGHT}
              overscanCount={10}
            >
              {LogRow}
            </FixedSizeList>
          ) : (
            <div className="flex h-[120px] items-center gap-3 px-4 text-slate-400">
              <TerminalSquare className="h-4 w-4" />
              No logs match the current filter.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
