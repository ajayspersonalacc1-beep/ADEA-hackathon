import Link from "next/link";
import {
  ArrowRight,
  Bot,
  GitBranch,
  ShieldCheck,
  Sparkles
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const highlights = [
  {
    title: "LLM-first orchestration",
    description:
      "Planner, diagnosis, repair, and optimization in one coordinated workflow.",
    icon: Bot
  },
  {
    title: "Autonomous repair loop",
    description:
      "Monitor failures, generate SQL fixes, retry execution, and learn from outcomes.",
    icon: ShieldCheck
  },
  {
    title: "Live lineage and metrics",
    description:
      "Inspect DAGs, logs, timing, and optimization signals from a single control center.",
    icon: GitBranch
  }
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
      <header className="flex items-center justify-between py-6">
        <BrandMark />
        <Link href="/dashboard">
          <Button variant="secondary">Open dashboard</Button>
        </Link>
      </header>
      <section className="grid flex-1 items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-sm text-primary">
            <Sparkles className="h-4 w-4" />
            Production-grade AI data engineering console
          </div>
          <div className="space-y-5">
            <h1 className="max-w-3xl font-display text-5xl font-semibold tracking-tight sm:text-6xl">
              Operate autonomous pipelines like a real modern data platform.
            </h1>
            <p className="max-w-2xl text-lg text-muted-foreground">
              ADEA plans SQL pipelines, executes them, detects anomalies,
              performs AI-assisted diagnosis and repair, then optimizes and learns
              from each run.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link href="/dashboard">
              <Button size="lg">
                Launch dashboard
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/dashboard#history">
              <Button variant="outline" size="lg">
                View pipeline history
              </Button>
            </Link>
          </div>
        </div>
        <div className="grid gap-4">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.title}>
                <CardContent className="flex items-start gap-4 p-6">
                  <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold">{item.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>
    </main>
  );
}
