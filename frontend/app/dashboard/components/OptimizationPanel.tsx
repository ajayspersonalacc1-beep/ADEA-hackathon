import { memo } from "react";
import { Lightbulb, Sparkles } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export const OptimizationPanel = memo(function OptimizationPanel({
  recommendations
}: {
  recommendations: string[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Optimization Suggestions</CardTitle>
        <CardDescription>
          AI-generated performance recommendations after successful pipeline execution.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {recommendations.length ? (
          recommendations.map((recommendation) => (
            <div
              key={recommendation}
              className="rounded-2xl border border-primary/20 bg-primary/10 p-4"
            >
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-white/70 p-2 text-primary dark:bg-slate-900/60">
                  <Lightbulb className="h-4 w-4" />
                </div>
                <p className="text-sm leading-6">{recommendation}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="flex items-center gap-3 rounded-2xl border border-border bg-background/40 p-4 text-sm text-muted-foreground">
            <Sparkles className="h-4 w-4" />
            No optimization recommendations available for this run.
          </div>
        )}
      </CardContent>
    </Card>
  );
});
