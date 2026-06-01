import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Wallet, TrendingUp, Sparkles, Building2, PlayCircle } from "lucide-react";

import { api, type OptimizeResponse } from "@/lib/api";
import { fmtInt, fmtMoneyCompact, fmtPct, fmtMoney } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { MetricTooltip } from "@/components/metric-tooltip";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/budget")({
  head: () => ({ meta: [{ title: "Budget Simulator — Outlet Intelligence" }] }),
  component: BudgetPage,
});

function BudgetPage() {
  const summary = useQuery({ queryKey: ["budget-summary"], queryFn: api.budgetSummary });
  const distributors = useQuery({ queryKey: ["budget-dist"], queryFn: api.budgetDistributors });

  const [budget, setBudget] = useState(5_000_000);
  const [bParam, setBParam] = useState(0.0005);
  const [result, setResult] = useState<OptimizeResponse | null>(null);

  const simulate = useMutation({
    mutationFn: () => api.budgetSimulate({ budget, b_param: bParam }),
    onSuccess: (data) => setResult(data),
  });

  const s = summary.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div>
        <h1 className="font-serif text-4xl text-foreground">Trade-Spend Optimiser</h1>
        <p className="text-sm text-muted-foreground">
          Inspect the current allocation, run "what-if" scenarios with different budgets, and see the
          recommended split across outlets.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Budget"
          term="Allocated Budget"
          value={s ? fmtMoneyCompact(s.total_budget) : "—"}
          icon={<Wallet className="h-4 w-4" />}
          accent
        />
        <KpiCard
          label="Expected Lift"
          term="Expected Lift"
          value={s ? fmtMoneyCompact(s.expected_total_lift) : "—"}
          hint="Volume gain (liters)"
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <KpiCard
          label="Avg ROI"
          term="ROI"
          value={s ? fmtPct(s.average_roi) : "—"}
          icon={<Sparkles className="h-4 w-4" />}
        />
        <KpiCard
          label="Active Outlets"
          value={s ? `${fmtInt(s.active_outlets)} / ${fmtInt(s.total_outlets)}` : "—"}
          hint="Funded vs. eligible"
          icon={<Building2 className="h-4 w-4" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="font-serif text-2xl">What-If Simulator</CardTitle>
          <p className="text-xs text-muted-foreground">
            Adjust the available budget and the solver elasticity, then re-run the optimisation.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <Label className="text-sm">Total Budget</Label>
                <span className="font-mono text-sm font-semibold">{fmtMoney(budget)}</span>
              </div>
              <Slider
                value={[budget]}
                min={500_000}
                max={20_000_000}
                step={100_000}
                onValueChange={(v) => setBudget(v[0])}
              />
              <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                <span>Rs 500K</span>
                <span>Rs 20M</span>
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center gap-1.5">
                <Label className="text-sm">Solver elasticity (b_param)</Label>
                <MetricTooltip term="b_param" />
              </div>
              <Input
                type="number"
                step="0.0001"
                min={0.00001}
                max={0.01}
                value={bParam}
                onChange={(e) => setBParam(parseFloat(e.target.value) || 0.0005)}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Lower = concentrate spend on best outlets. Higher = spread across more outlets.
              </p>
            </div>
          </div>
          <div>
            <Button onClick={() => simulate.mutate()} disabled={simulate.isPending} className="gap-2">
              <PlayCircle className="h-4 w-4" />
              {simulate.isPending ? "Running optimiser…" : "Run Simulation"}
            </Button>
          </div>

          {result && (
            <div className="space-y-4 border-t border-border pt-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Total Allocated" value={fmtMoneyCompact(result.total_allocated)} accent />
                <KpiCard label="Expected Lift" value={`${fmtInt(result.expected_lift)} L`} />
                <KpiCard label="Active Outlets" value={fmtInt(result.active_outlets)} />
                <KpiCard label="Avg ROI" value={fmtPct(result.avg_roi)} />
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  Top 15 allocations
                </h3>
                <Card>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-secondary/40">
                          <TableHead>Outlet</TableHead>
                          <TableHead className="text-right">Budget</TableHead>
                          <TableHead className="text-right">Expected Lift</TableHead>
                          <TableHead className="text-right">ROI</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {[...result.allocations]
                          .sort((a, b) => b.Allocated_Budget - a.Allocated_Budget)
                          .slice(0, 15)
                          .map((a) => (
                            <TableRow key={a.Outlet_ID}>
                              <TableCell className="font-mono text-xs">{a.Outlet_ID}</TableCell>
                              <TableCell className="text-right tabular-nums">
                                {fmtMoney(a.Allocated_Budget)}
                              </TableCell>
                              <TableCell className="text-right tabular-nums">
                                {fmtInt(a.Expected_Lift)} L
                              </TableCell>
                              <TableCell className="text-right tabular-nums">
                                {fmtPct(a.ROI)}
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="font-serif text-2xl">Spend by Distributor</CardTitle>
          <p className="text-xs text-muted-foreground">
            Where the current trade-spend allocation is concentrated.
          </p>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-secondary/40">
                <TableHead>Distributor</TableHead>
                <TableHead className="text-right">Outlets</TableHead>
                <TableHead className="text-right">Active</TableHead>
                <TableHead className="text-right">Total Spend</TableHead>
                <TableHead className="text-right">Share</TableHead>
                <TableHead className="text-right">Lift</TableHead>
                <TableHead className="text-right">Avg ROI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(distributors.data ?? []).map((d) => (
                <TableRow key={d.name}>
                  <TableCell className="font-mono text-xs font-semibold">{d.name}</TableCell>
                  <TableCell className="text-right tabular-nums">{fmtInt(d.total_outlets)}</TableCell>
                  <TableCell className="text-right tabular-nums">{fmtInt(d.active_outlets)}</TableCell>
                  <TableCell className="text-right tabular-nums">{fmtMoney(d.total_spend)}</TableCell>
                  <TableCell className="text-right tabular-nums">{d.share_of_spend.toFixed(1)}%</TableCell>
                  <TableCell className="text-right tabular-nums">{fmtInt(d.volume_lift)} L</TableCell>
                  <TableCell className="text-right tabular-nums">{fmtPct(d.avg_roi)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
