import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";
import { Building2, Wallet, TrendingUp, Gauge, Sparkles, MapPin } from "lucide-react";

import { api } from "@/lib/api";
import { fmtInt, fmtMoneyCompact, fmtNum, fmtPct } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricTooltip } from "@/components/metric-tooltip";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [{ title: "Executive Dashboard — Outlet Intelligence" }],
  }),
  component: Dashboard,
});

function Dashboard() {
  const summary = useQuery({ queryKey: ["dash-summary"], queryFn: api.dashboardSummary });
  const distributors = useQuery({ queryKey: ["dash-dist"], queryFn: api.dashboardDistributors });
  const provinces = useQuery({ queryKey: ["dash-prov"], queryFn: api.dashboardProvinces });

  const s = summary.data;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="space-y-1">
        <h1 className="font-serif text-4xl text-foreground">Executive Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          A single view of network performance, latent opportunity, and trade-spend efficiency across
          your beverage distribution territory.
        </p>
      </div>

      {summary.isError && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-4 text-sm text-destructive">
            Could not load dashboard data. Verify that the FastAPI backend is running at the
            configured base URL.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Outlets"
          value={s ? fmtInt(s.total_outlets) : "—"}
          hint="Total stores in network"
          icon={<Building2 className="h-4 w-4" />}
        />
        <KpiCard
          label="Active Outlets"
          value={s ? fmtInt(s.total_active_outlets) : "—"}
          hint="Receiving promotional spend"
          icon={<MapPin className="h-4 w-4" />}
        />
        <KpiCard
          label="Budget Allocated"
          value={s ? fmtMoneyCompact(s.total_budget_allocated) : "—"}
          hint="Recommended trade spend"
          icon={<Wallet className="h-4 w-4" />}
          term="Allocated Budget"
          accent
        />
        <KpiCard
          label="Expected Lift"
          value={s ? fmtMoneyCompact(s.expected_total_lift) : "—"}
          hint="Forecasted volume gain"
          icon={<TrendingUp className="h-4 w-4" />}
          term="Expected Lift"
        />
        <KpiCard
          label="Avg ROI"
          value={s ? fmtPct(s.average_roi) : "—"}
          hint="Lift per rupee spent"
          icon={<Sparkles className="h-4 w-4" />}
          term="ROI"
        />
        <KpiCard
          label="Avg Efficiency"
          value={s ? fmtPct(s.avg_efficiency_score) : "—"}
          hint="Sales vs. potential"
          icon={<Gauge className="h-4 w-4" />}
          term="Efficiency Score"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-serif text-2xl">
              Provinces by Opportunity
              <MetricTooltip term="Opportunity Gap" />
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Untapped sales potential (in liters) by region. Taller bars = bigger growth runway.
            </p>
          </CardHeader>
          <CardContent>
            <GapChart data={provinces.data ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-serif text-2xl">
              Distributors by Opportunity
              <MetricTooltip term="Opportunity Gap" />
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              The distributors with the largest aggregated opportunity gap — focus accounts.
            </p>
          </CardHeader>
          <CardContent>
            <GapChart data={(distributors.data ?? []).slice(0, 10)} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-2xl">Provincial Efficiency</CardTitle>
            <p className="text-xs text-muted-foreground">
              Average sales-vs-potential score per province. Lower scores indicate stronger lift
              opportunity.
            </p>
          </CardHeader>
          <CardContent>
            <EfficiencyChart data={provinces.data ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-2xl">Top Distributors — Avg Potential</CardTitle>
            <p className="text-xs text-muted-foreground">
              Average predicted volume potential per outlet, by distributor (top 10).
            </p>
          </CardHeader>
          <CardContent>
            <PotentialChart data={(distributors.data ?? []).slice(0, 10)} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

type Row = { name: string; total_opportunity_gap: number; avg_efficiency: number; avg_potential: number };

function GapChart({ data }: { data: Row[] }) {
  const sorted = [...data].sort((a, b) => b.total_opportunity_gap - a.total_opportunity_gap);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={sorted} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" tickFormatter={(v) => fmtNum(v / 1000) + "k"} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any) => [fmtInt(v) + " L", "Opportunity Gap"]}
        />
        <Bar dataKey="total_opportunity_gap" radius={[4, 4, 0, 0]} fill="var(--primary)" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function EfficiencyChart({ data }: { data: Row[] }) {
  const sorted = [...data].sort((a, b) => b.avg_efficiency - a.avg_efficiency);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={sorted} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" tickFormatter={(v) => fmtPct(v, 0)} domain={[0, 1]} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any) => [fmtPct(v), "Avg Efficiency"]}
        />
        <Bar dataKey="avg_efficiency" radius={[4, 4, 0, 0]}>
          {sorted.map((d, i) => (
            <Cell
              key={i}
              fill={d.avg_efficiency >= 0.6 ? "var(--success)" : d.avg_efficiency >= 0.4 ? "var(--accent)" : "var(--destructive)"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function PotentialChart({ data }: { data: Row[] }) {
  const sorted = [...data].sort((a, b) => b.avg_potential - a.avg_potential);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 8, right: 8, left: 40, bottom: 8 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" width={80} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any) => [fmtInt(v) + " L", "Avg Potential"]}
        />
        <Bar dataKey="avg_potential" radius={[0, 4, 4, 0]} fill="var(--accent)" />
      </BarChart>
    </ResponsiveContainer>
  );
}
