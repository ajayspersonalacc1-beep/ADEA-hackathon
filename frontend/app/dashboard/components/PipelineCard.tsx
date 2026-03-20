"use client";

import { memo } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, Clock3, Layers3, PlaySquare } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export const PipelineCard = memo(function PipelineCard({
  title,
  value,
  hint,
  icon,
  accent = "primary"
}: {
  title: string;
  value: string | number;
  hint: string;
  icon?: "status" | "duration" | "steps" | "failures";
  accent?: "primary" | "success" | "warning" | "error";
}) {
  const Icon =
    icon === "duration"
      ? Clock3
      : icon === "steps"
        ? Layers3
        : icon === "failures"
          ? AlertTriangle
          : icon === "status"
            ? PlaySquare
            : Activity;

  const tone =
    accent === "success"
      ? "bg-success/15 text-success"
      : accent === "warning"
        ? "bg-warning/15 text-warning"
        : accent === "error"
          ? "bg-error/15 text-error"
          : "bg-primary/15 text-primary";

  return (
    <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.18 }}>
      <Card className="h-full">
        <CardContent className="flex items-start justify-between gap-4 p-6">
          <div>
            <p className="panel-header">{title}</p>
            <div className="mt-4 text-3xl font-semibold tracking-tight">{value}</div>
            <p className="mt-2 text-sm text-muted-foreground">{hint}</p>
          </div>
          <div className={`rounded-2xl p-3 ${tone}`}>
            <Icon className="h-5 w-5" />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
});
