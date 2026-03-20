"use client";

import { Loader2, PlayCircle, WandSparkles } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

const DEMO_PROMPT =
  "__adea_demo__ build customer lifetime value analytics pipeline";

export function PromptInput({
  onSubmit,
  loading
}: {
  onSubmit: (prompt: string) => Promise<void>;
  loading: boolean;
}) {
  const [value, setValue] = useState("Build sales analytics pipeline");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Prompt</CardTitle>
        <CardDescription>
          Describe the analytics pipeline you want ADEA to plan and execute.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Build revenue reporting pipeline using available sales tables"
        />
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => void onSubmit(value)} disabled={loading || !value.trim()}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running pipeline
              </>
            ) : (
              <>
                <PlayCircle className="h-4 w-4" />
                Run pipeline
              </>
            )}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setValue(DEMO_PROMPT);
              void onSubmit(DEMO_PROMPT);
            }}
            disabled={loading}
          >
            <WandSparkles className="h-4 w-4" />
            Demo mode
          </Button>
        </div>
        {loading ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-primary"
          >
            ADEA is orchestrating planner, executor, repair loop, and optimization.
          </motion.div>
        ) : null}
      </CardContent>
    </Card>
  );
}
