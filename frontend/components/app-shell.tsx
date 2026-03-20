import Link from "next/link";
import type { ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Clock3,
  LayoutDashboard,
  Settings2
} from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";

const navigation = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Pipelines", href: "/dashboard#history", icon: Activity },
  { label: "Metrics", href: "/dashboard#metrics", icon: BarChart3 },
  { label: "Logs", href: "/dashboard#logs", icon: Clock3 },
  { label: "Settings", href: "/dashboard#settings", icon: Settings2 }
];

export function AppShell({
  children,
  headerContent
}: {
  children: ReactNode;
  headerContent?: ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <aside className="glass-panel hidden w-72 flex-col p-5 lg:flex">
          <BrandMark />
          <div className="mt-8 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-muted-foreground transition hover:bg-primary/10 hover:text-foreground"
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
          <div className="mt-auto rounded-2xl border border-primary/20 bg-primary/10 p-4">
            <p className="text-sm font-semibold text-foreground">Live Agent Mode</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Monitor planning, repair, retry, optimization, and artifacts from one control surface.
            </p>
          </div>
        </aside>
        <div className="flex min-h-screen flex-1 flex-col gap-6">
          <header className="glass-panel flex items-center justify-between px-5 py-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.28em] text-primary">
                AI Data Platform
              </p>
              <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">
                Autonomous pipeline control center
              </h1>
            </div>
            <div className="flex items-center gap-3">
              {headerContent}
              <ThemeToggle />
            </div>
          </header>
          <main className="pb-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
