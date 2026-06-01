import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { MetricTooltip } from "@/components/metric-tooltip";

export function KpiCard({
  label,
  value,
  hint,
  icon,
  term,
  accent,
  progress,
  progressColor = "bg-primary",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  term?: string;
  accent?: boolean;
  progress?: number;
  progressColor?: string;
}) {
  return (
    <Card className="relative overflow-hidden border-border/60 shadow-sm flex flex-col justify-between h-full">
      {accent && <div className="absolute inset-x-0 top-0 h-1 bg-accent" />}
      <CardContent className="p-5 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {label}
              </span>
              {term && <MetricTooltip term={term} />}
            </div>
            {icon && <span className="text-primary/70">{icon}</span>}
          </div>
          <div className="mt-2 font-serif text-3xl font-medium text-foreground">{value}</div>
        </div>
        <div className="mt-3">
          {progress !== undefined && (
            <div className="mb-1.5 h-1.5 w-full rounded-full bg-secondary/80 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
                style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
              />
            </div>
          )}
          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
