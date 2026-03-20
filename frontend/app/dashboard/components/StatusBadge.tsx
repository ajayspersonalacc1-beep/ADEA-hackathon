import { memo } from "react";

import { Badge } from "@/components/ui/badge";

export const StatusBadge = memo(function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();

  if (normalized === "success") {
    return <Badge variant="success">{status}</Badge>;
  }
  if (
    normalized === "failed" ||
    normalized === "unrecoverable" ||
    normalized === "anomaly_detected"
  ) {
    return <Badge variant="error">{status}</Badge>;
  }
  if (normalized === "repaired" || normalized === "diagnosed") {
    return <Badge variant="warning">{status}</Badge>;
  }
  if (normalized === "running" || normalized === "pending") {
    return <Badge variant="muted">{status}</Badge>;
  }

  return <Badge>{status}</Badge>;
});
