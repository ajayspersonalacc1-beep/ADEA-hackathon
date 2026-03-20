import { Bot, Sparkles } from "lucide-react";

export function BrandMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-glass">
        <Bot className="h-5 w-5" />
      </div>
      <div>
        <div className="flex items-center gap-2">
          <span className="font-semibold tracking-[0.28em] text-primary">ADEA</span>
          <Sparkles className="h-3.5 w-3.5 text-warning" />
        </div>
        <p className="text-xs text-muted-foreground">
          Autonomous Data Engineer Agent
        </p>
      </div>
    </div>
  );
}
