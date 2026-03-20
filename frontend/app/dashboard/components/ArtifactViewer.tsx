"use client";

import { Download, FileText, Image as ImageIcon, ScrollText } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

function downloadText(filename: string, contents: string) {
  const blob = new Blob([contents], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ArtifactViewer({
  pipelineId,
  report,
  logs
}: {
  pipelineId: string;
  report: string;
  logs: string[];
}) {
  return (
    <Card id="settings">
      <CardHeader>
        <CardTitle>Artifacts</CardTitle>
        <CardDescription>
          Download pipeline report, terminal logs, and inspect graph artifact conventions.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-background/40 p-4">
          <div className="flex items-center gap-3">
            <FileText className="h-4 w-4 text-primary" />
            <p className="font-medium">Pipeline report</p>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Client-generated report summary for the selected run.
          </p>
          <Button
            className="mt-4 w-full"
            variant="secondary"
            onClick={() => downloadText(`${pipelineId}_report.txt`, report)}
          >
            <Download className="h-4 w-4" />
            Download report
          </Button>
        </div>
        <div className="rounded-2xl border border-border bg-background/40 p-4">
          <div className="flex items-center gap-3">
            <ScrollText className="h-4 w-4 text-success" />
            <p className="font-medium">Execution logs</p>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Export the latest terminal logs for demos or incident review.
          </p>
          <Button
            className="mt-4 w-full"
            variant="secondary"
            onClick={() => downloadText(`${pipelineId}_logs.txt`, logs.join("\n"))}
          >
            <Download className="h-4 w-4" />
            Download logs
          </Button>
        </div>
        <div className="rounded-2xl border border-border bg-background/40 p-4">
          <div className="flex items-center gap-3">
            <ImageIcon className="h-4 w-4 text-warning" />
            <p className="font-medium">Pipeline graph</p>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Backend graph artifact convention: output/{pipelineId}_graph.png.
          </p>
          <div className="mt-4 rounded-xl border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
            DAG is rendered live in the visualization panel for the selected run.
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
