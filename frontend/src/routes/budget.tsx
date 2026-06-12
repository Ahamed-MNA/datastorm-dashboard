import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Wallet, TrendingUp, Sparkles, Building2, PlayCircle, Calendar, CheckCircle } from "lucide-react";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/budget")({
  head: () => ({ meta: [{ title: "Budget Simulator — Outlet Intelligence" }] }),
  component: BudgetPage,
});

const getSelectionReason = (gap: number, roi: number, school: string, comp: string) => {
  if (gap > 200 && roi > 0.7) {
    return "High unrealized demand and strong projected ROI.";
  }
  if (roi > 0.8) {
    return "Outstanding return on investment score coupled with stable baseline demand.";
  }
  if (school === "High" || school === "Medium") {
    return "Strong local demand driven by proximity to educational hubs and commercial centers.";
  }
  if (comp === "Low") {
    return "High potential opportunity with minimal competitor presence in the immediate area.";
  }
  return "Steady sales opportunity with balanced market saturation and consistent performance metrics.";
};

const PROVINCES = ["Western", "Central", "North Western", "Southern"];
const OUTLET_TYPES = ["Grocery", "Hotel", "Pharmacy", "Kiosk", "Eatery", "Bakery", "SMMT"];
const OUTLET_SIZES = ["Medium", "Small", "Large", "Extra Large", "Unknown"];

function BudgetPage() {
  const navigate = useNavigate();
  const summary = useQuery({ queryKey: ["budget-summary"], queryFn: api.budgetSummary });
  const distributors = useQuery({ queryKey: ["budget-dist"], queryFn: api.budgetDistributors });

  // Simulator States
  const [budget, setBudget] = useState(5_000_000);
  const [bParam, setBParam] = useState(0.0005);
  const [province, setProvince] = useState("Western");
  const [outletType, setOutletType] = useState<string>("__all");
  const [outletSize, setOutletSize] = useState<string>("__all");
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(null);

  // Dialog States for Campaign Creation
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [campaignName, setCampaignName] = useState("");
  
  const todayStr = new Date().toISOString().split("T")[0];
  const threeMonthsLaterStr = (() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 3);
    return d.toISOString().split("T")[0];
  })();
  
  const [startDate, setStartDate] = useState(todayStr);
  const [endDate, setEndDate] = useState(threeMonthsLaterStr);
  const [pilotSize, setPilotSize] = useState(20);

  const simulate = useMutation({
    mutationFn: () =>
      api.budgetSimulate({
        budget,
        b_param: bParam,
        province,
        outlet_type: outletType === "__all" ? undefined : outletType,
        outlet_size: outletSize === "__all" ? undefined : outletSize,
      }),
    onSuccess: (data) => setResult(data),
  });

  const createCampaign = useMutation({
    mutationFn: () =>
      api.createCampaignFromSimulation({
        campaign_name: campaignName,
        province,
        outlet_type: outletType === "__all" ? undefined : outletType,
        outlet_size: outletSize === "__all" ? undefined : outletSize,
        total_budget: result?.total_allocated ?? budget,
        b_param: bParam,
        start_date: startDate,
        end_date: endDate,
        top_n: pilotSize,
      }),
    onSuccess: () => {
      setCreateDialogOpen(false);
      setCampaignName("");
      navigate({ to: "/monitoring" });
    },
  });

  const xaiQuery = useQuery({
    queryKey: ["xai", selectedOutletId],
    queryFn: () => api.xai(selectedOutletId!),
    enabled: !!selectedOutletId,
    retry: false,
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
            Adjust the available budget, solver elasticity, and segment filters, then re-run the optimisation.
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

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3 border-t border-border pt-4">
            <div className="space-y-2">
              <Label className="text-sm">Province</Label>
              <Select value={province} onValueChange={setProvince}>
                <SelectTrigger>
                  <SelectValue placeholder="Select Province" />
                </SelectTrigger>
                <SelectContent>
                  {PROVINCES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p} Province
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm">Outlet Type</Label>
              <Select value={outletType} onValueChange={setOutletType}>
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">All Types</SelectItem>
                  {OUTLET_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm">Outlet Size</Label>
              <Select value={outletSize} onValueChange={setOutletSize}>
                <SelectTrigger>
                  <SelectValue placeholder="All Sizes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">All Sizes</SelectItem>
                  {OUTLET_SIZES.map((sz) => (
                    <SelectItem key={sz} value={sz}>
                      {sz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Button onClick={() => simulate.mutate()} disabled={simulate.isPending} className="gap-2">
              <PlayCircle className="h-4 w-4" />
              {simulate.isPending ? "Running optimiser…" : "Run Simulation"}
            </Button>
          </div>

          {result && (
            <div className="space-y-6 border-t border-border pt-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-primary/5 rounded-lg p-4 border border-primary/20">
                <div>
                  <h3 className="font-serif text-lg text-primary flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-primary" />
                    Optimisation Simulation Ready
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    Segment: {province} Province &middot; {outletType === "__all" ? "All Types" : outletType} &middot; {outletSize === "__all" ? "All Sizes" : outletSize}
                  </p>
                </div>
                <Button onClick={() => setCreateDialogOpen(true)} className="gap-2 shrink-0">
                  <Sparkles className="h-4 w-4" />
                  Create Campaign from Simulation
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Total Allocated" value={fmtMoneyCompact(result.total_allocated)} accent />
                <KpiCard label="Expected Lift" value={`${fmtInt(result.expected_lift)} L`} />
                <KpiCard
                  label="Active Outlets"
                  value={`${fmtInt(result.active_outlets)} / ${fmtInt(result.allocations.length)}`}
                  hint="Funded vs. eligible"
                />
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
                              <TableCell 
                                className="font-mono text-xs font-semibold text-primary hover:underline cursor-pointer"
                                onClick={() => setSelectedOutletId(a.Outlet_ID)}
                              >
                                {a.Outlet_ID}
                              </TableCell>
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

      {/* Campaign Creation Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-xl">Create Pilot Campaign</DialogTitle>
            <DialogDescription>
              Launch a live pilot campaign using this simulation. This will optimize the target outlets, seed weekly monitoring data, and set it to Active.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="campaign_name">Campaign Name</Label>
              <Input
                id="campaign_name"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                placeholder="e.g. Q3 Western Grocery Campaign"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="pilot_size">Pilot Size (Treatment Outlets)</Label>
              <Input
                id="pilot_size"
                type="number"
                min={1}
                max={100}
                value={pilotSize}
                onChange={(e) => setPilotSize(parseInt(e.target.value) || 20)}
              />
              <p className="text-[10px] text-muted-foreground">
                Matches the top N simulated outlets by budget size. An equal number of control outlets will be paired.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              disabled={createCampaign.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => createCampaign.mutate()}
              disabled={!campaignName || createCampaign.isPending}
              className="gap-2"
            >
              {createCampaign.isPending ? "Creating..." : "Confirm & Launch"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Selection Drivers Dialog */}
      <Dialog open={!!selectedOutletId} onOpenChange={(open) => { if (!open) setSelectedOutletId(null); }}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-xl flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Selection Drivers
            </DialogTitle>
            <DialogDescription>
              Key attributes explaining the budget allocation decision for outlet <span className="font-mono font-semibold text-foreground">{selectedOutletId}</span>.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-4">
            {xaiQuery.isLoading && (
              <div className="flex flex-col items-center justify-center py-6 space-y-2">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
                <span className="text-xs text-muted-foreground">Loading selection drivers...</span>
              </div>
            )}

            {xaiQuery.isError && (
              <div className="text-center py-4 text-xs text-destructive">
                Failed to load drivers for this outlet.
              </div>
            )}

            {xaiQuery.data && (() => {
              const xaiData = xaiQuery.data;
              const currentAllocation = result?.allocations.find(a => a.Outlet_ID === selectedOutletId);
              
              const signals = xaiData.payload?.local_signals || {};
              const eduKey = Object.keys(signals).find(k => k.toLowerCase().includes('education') || k.toLowerCase().includes('school'));
              const eduVal = eduKey ? signals[eduKey] : 0;
              const schoolGravity = eduVal > 50 ? "High" : eduVal > 0 ? "Medium" : "Low";
              
              const compKey = Object.keys(signals).find(k => k.toLowerCase().includes('competitor_count') || k.toLowerCase().includes('competitor'));
              const compVal = compKey ? signals[compKey] : 0;
              const competition = compVal > 200 ? "High" : compVal > 80 ? "Medium" : "Low";

              const roiVal = currentAllocation?.ROI ?? xaiData.efficiency_score;
              const gapVal = currentAllocation?.Expected_Lift ?? xaiData.opportunity_gap;

              const reason = getSelectionReason(gapVal, roiVal, schoolGravity, competition);

              return (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-secondary/40 p-2.5 rounded-lg">
                      <span className="text-[10px] text-muted-foreground block uppercase font-medium">Potential Gap</span>
                      <span className="text-sm font-semibold font-mono">+{fmtInt(gapVal)}L</span>
                    </div>
                    <div className="bg-secondary/40 p-2.5 rounded-lg">
                      <span className="text-[10px] text-muted-foreground block uppercase font-medium">ROI Score</span>
                      <span className="text-sm font-semibold font-mono">{roiVal.toFixed(2)}</span>
                    </div>
                    <div className="bg-secondary/40 p-2.5 rounded-lg">
                      <span className="text-[10px] text-muted-foreground block uppercase font-medium">School Gravity</span>
                      <span className={`text-sm font-semibold ${schoolGravity === 'High' ? 'text-emerald-500' : schoolGravity === 'Medium' ? 'text-amber-500' : 'text-muted-foreground'}`}>
                        {schoolGravity}
                      </span>
                    </div>
                    <div className="bg-secondary/40 p-2.5 rounded-lg">
                      <span className="text-[10px] text-muted-foreground block uppercase font-medium">Competition</span>
                      <span className={`text-sm font-semibold ${competition === 'High' ? 'text-rose-500' : competition === 'Medium' ? 'text-amber-500' : 'text-emerald-500'}`}>
                        {competition}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1.5 border-t border-border pt-3">
                    <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Reason</h4>
                    <p className="text-xs font-medium text-foreground bg-primary/5 p-2 rounded border border-primary/10 animate-fade-in">
                      {reason}
                    </p>
                  </div>
                </div>
              );
            })()}
          </div>
          <DialogFooter>
            <Button onClick={() => setSelectedOutletId(null)} variant="outline">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
