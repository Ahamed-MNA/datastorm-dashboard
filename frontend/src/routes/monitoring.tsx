import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { 
  Activity, Plus, Play, ShieldAlert, Sparkles, TrendingUp, Wallet, CheckCircle2, 
  ArrowRight, RefreshCw, AlertCircle, AlertTriangle, HeartPulse
} from "lucide-react";
import { api, type Campaign, type CampaignCreateInput } from "@/lib/api";
import { fmtMoney, fmtMoneyCompact, fmtInt, fmtPct } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, ScatterChart, Scatter, ZAxis 
} from "recharts";

export const Route = createFileRoute("/monitoring")({
  head: () => ({ meta: [{ title: "Campaign Monitoring — Outlet Intelligence" }] }),
  component: MonitoringPage,
});

const PROVINCES = [
  "Western",
  "Southern",
  "Central",
  "North Western",
  "Eastern",
  "North Central",
  "Uva",
  "Sabaragamuwa",
  "Northern"
];

function MonitoringPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [pilotN, setPilotN] = useState(20);
  
  // Create Campaign Form States
  const [name, setName] = useState("");
  const [province, setProvince] = useState("");
  const [budget, setBudget] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Queries
  const campaignsQuery = useQuery({
    queryKey: ["campaigns"],
    queryFn: api.listCampaigns,
  });

  const activeId = selectedId || (campaignsQuery.data && campaignsQuery.data.length > 0 ? campaignsQuery.data[campaignsQuery.data.length - 1].campaign_id : null);

  const activeCampaignQuery = useQuery({
    queryKey: ["campaign-details", activeId],
    queryFn: () => api.campaignDetails(activeId!),
    enabled: !!activeId,
  });

  const monitoringQuery = useQuery({
    queryKey: ["campaign-monitoring", activeId],
    queryFn: () => api.getCampaignMonitoring(activeId!),
    enabled: !!activeId && activeCampaignQuery.data?.status !== "Draft",
  });

  const reallocationsQuery = useQuery({
    queryKey: ["campaign-reallocations", activeId],
    queryFn: () => api.getReallocations(activeId!),
    enabled: !!activeId && activeCampaignQuery.data?.status === "Active",
  });

  // Mutations
  const createCampaign = useMutation({
    mutationFn: (body: CampaignCreateInput) => api.createCampaign(body),
    onSuccess: (data) => {
      toast.success("Campaign created successfully!");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setSelectedId(data.campaign_id);
      setCreateOpen(false);
      // Reset form
      setName("");
      setProvince("");
      setBudget("");
      setStartDate("");
      setEndDate("");
    },
    onError: () => {
      toast.error("Failed to create campaign.");
    }
  });

  const startPilot = useMutation({
    mutationFn: ({ id, topN }: { id: number; topN: number }) => api.startPilot(id, topN),
    onSuccess: () => {
      toast.success("Pilot program started successfully! Matching control group and snapshots initialized.");
      queryClient.invalidateQueries({ queryKey: ["campaign-details", activeId] });
      queryClient.invalidateQueries({ queryKey: ["campaign-monitoring", activeId] });
      queryClient.invalidateQueries({ queryKey: ["campaign-reallocations", activeId] });
    },
    onError: (err: any) => {
      toast.error("Failed to start pilot: " + err.message);
    }
  });

  const applyReallocations = useMutation({
    mutationFn: (id: number) => api.applyReallocations(id),
    onSuccess: () => {
      toast.success("Reallocation recommendations applied! Budgets shifted and monitoring updated.");
      queryClient.invalidateQueries({ queryKey: ["campaign-monitoring", activeId] });
      queryClient.invalidateQueries({ queryKey: ["campaign-reallocations", activeId] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-did", activeId] });
    },
    onError: (err: any) => {
      toast.error("Failed to apply recommendations: " + err.message);
    }
  });

  const endCampaign = useMutation({
    mutationFn: (id: number) => api.endCampaign(id),
    onSuccess: () => {
      toast.success("Campaign ended successfully! Status set to Completed.");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["campaign-details", activeId] });
      queryClient.invalidateQueries({ queryKey: ["campaign-monitoring", activeId] });
    },
    onError: (err: any) => {
      toast.error("Failed to end campaign: " + err.message);
    }
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !province || !budget || !startDate || !endDate) {
      toast.error("Please fill in all fields.");
      return;
    }
    createCampaign.mutate({
      campaign_name: name,
      province,
      total_budget: parseFloat(budget),
      start_date: startDate,
      end_date: endDate
    });
  };

  const currentCampaign = activeCampaignQuery.data;
  const m = monitoringQuery.data;
  const recs = reallocationsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-serif text-4xl text-foreground">Pilot Campaign Monitoring</h1>
          <p className="text-sm text-muted-foreground">
            Create pilot campaigns, assign budgets to target outlets, match control groups, and track performance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {campaignsQuery.data && campaignsQuery.data.length > 0 && (
            <Select 
              value={String(activeId ?? "")} 
              onValueChange={(val) => setSelectedId(parseInt(val))}
            >
              <SelectTrigger className="w-[250px] bg-card">
                <SelectValue placeholder="Select campaign" />
              </SelectTrigger>
              <SelectContent>
                {campaignsQuery.data.map((c) => (
                  <SelectItem key={c.campaign_id} value={String(c.campaign_id)}>
                    {c.campaign_name} ({c.status})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-1">
                <Plus className="h-4 w-4" /> Create Campaign
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle className="font-serif text-xl">Create Campaign</DialogTitle>
                <DialogDescription>
                  Configure a new marketing pilot. This will create a draft campaign that you can customize and launch.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="c_name">Campaign Name</Label>
                  <Input 
                    id="c_name" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)} 
                    placeholder="e.g. Western Grocery Booster" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="c_province">Province</Label>
                  <Select value={province} onValueChange={setProvince}>
                    <SelectTrigger id="c_province">
                      <SelectValue placeholder="Select province" />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVINCES.map((p) => (
                        <SelectItem key={p} value={p}>{p}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="c_budget">Total Budget (LKR)</Label>
                  <Input 
                    id="c_budget" 
                    type="number"
                    value={budget} 
                    onChange={(e) => setBudget(e.target.value)} 
                    placeholder="e.g. 1500000" 
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="c_start">Start Date</Label>
                    <Input 
                      id="c_start" 
                      type="date"
                      value={startDate} 
                      onChange={(e) => setStartDate(e.target.value)} 
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="c_end">End Date</Label>
                    <Input 
                      id="c_end" 
                      type="date"
                      value={endDate} 
                      onChange={(e) => setEndDate(e.target.value)} 
                    />
                  </div>
                </div>
                <DialogFooter className="pt-4">
                  <Button type="submit" disabled={createCampaign.isPending}>
                    {createCampaign.isPending ? "Creating..." : "Save Draft"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {campaignsQuery.isLoading && (
        <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-border bg-card">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {campaignsQuery.data && campaignsQuery.data.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card p-10 text-center">
          <Activity className="h-12 w-12 text-muted-foreground/60" />
          <h2 className="mt-4 text-lg font-semibold">No Campaigns Found</h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-sm">
            Create your first draft campaign to begin ranking high-potential outlets, matching control groups, and running pilots.
          </p>
        </div>
      )}

      {currentCampaign && (
        <div className="space-y-6">
          {/* Status Header */}
          <div className="flex flex-col justify-between gap-4 rounded-lg border border-border bg-card p-6 shadow-sm sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-serif">{currentCampaign.campaign_name}</h2>
                <Badge variant={
                  currentCampaign.status === "Active" ? "default" :
                  currentCampaign.status === "Completed" ? "secondary" : "outline"
                }>
                  {currentCampaign.status}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Province: <span className="font-semibold text-foreground">{currentCampaign.province}</span> &middot; 
                Timeline: <span className="font-semibold text-foreground">{currentCampaign.start_date} to {currentCampaign.end_date}</span> &middot;
                Budget: <span className="font-semibold text-foreground">{fmtMoney(currentCampaign.total_budget)}</span>
              </p>
            </div>

            {currentCampaign.status === "Draft" && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="top_n" className="text-xs">Outlets:</Label>
                  <Input 
                    id="top_n"
                    type="number"
                    value={pilotN}
                    onChange={(e) => setPilotN(Math.max(1, parseInt(e.target.value) || 20))}
                    className="h-8 w-16 text-center text-xs"
                  />
                </div>
                <Button 
                  onClick={() => startPilot.mutate({ id: currentCampaign.campaign_id, topN: pilotN })}
                  disabled={startPilot.isPending}
                  className="gap-1.5 h-9"
                  variant="default"
                >
                  <Play className="h-3.5 w-3.5 fill-current" /> Start Pilot Campaign
                </Button>
              </div>
            )}

            {currentCampaign.status === "Active" && (
              <div className="flex items-center gap-3">
                <Button 
                  onClick={() => endCampaign.mutate(currentCampaign.campaign_id)}
                  disabled={endCampaign.isPending}
                  className="gap-1.5 h-9"
                  variant="destructive"
                >
                  End Campaign
                </Button>
              </div>
            )}
          </div>

          {currentCampaign.status !== "Draft" && m && (
            <>
              {/* KPIs */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
                <KpiCard
                  label="Allocated Budget"
                  value={fmtMoneyCompact(m.allocated_budget)}
                  icon={<Wallet className="h-4 w-4" />}
                  accent
                />
                <KpiCard
                  label="Expected Lift"
                  value={`${fmtInt(m.expected_lift)} L`}
                  icon={<TrendingUp className="h-4 w-4" />}
                />
                <KpiCard
                  label="Actual Lift"
                  value={`${fmtInt(m.actual_lift)} L`}
                  hint={`ROI: ${m.roi.toFixed(4)}`}
                  icon={<Sparkles className="h-4 w-4" />}
                />
                <KpiCard
                  label="Actual Revenue"
                  value={fmtMoneyCompact(m.actual_revenue)}
                  icon={<Wallet className="h-4 w-4" />}
                />
                <KpiCard
                  label="Underperforming"
                  value={String(m.underperforming_outlets)}
                  hint="Budgets needing attention"
                  icon={<ShieldAlert className="h-4 w-4" />}
                  className={m.underperforming_outlets > 0 ? "border-destructive/30 bg-destructive/5" : ""}
                />
                <KpiCard
                  label="Campaign Health"
                  value={m.health_score !== undefined ? `${m.health_score}%` : "—"}
                  progress={m.health_score}
                  progressColor={m.health_score < 60 ? "bg-destructive" : m.health_score < 80 ? "bg-amber-500" : "bg-green-500"}
                  hint={`Lift: ${m.health_score_details?.lift_achievement}% | ROI: ${m.health_score_details?.roi_achievement}% | Control: ${m.health_score_details?.treatment_vs_control}% | Part: ${m.health_score_details?.outlet_participation}%`}
                  icon={<HeartPulse className="h-4 w-4" />}
                />
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="font-serif text-lg">Expected vs Actual Lift (Liters)</CardTitle>
                    <CardDescription>Performance comparison per outlet in the pilot</CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={m.charts.expected_vs_actual}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                        <XAxis dataKey="outlet_id" stroke="#888888" fontSize={10} tickLine={false} />
                        <YAxis stroke="#888888" fontSize={10} tickLine={false} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        <Bar dataKey="expected_lift" name="Expected Lift" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} opacity={0.7} />
                        <Bar dataKey="actual_lift" name="Actual Lift" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="font-serif text-lg">Budget vs ROI (Scatter)</CardTitle>
                    <CardDescription>Efficiency (Lift per LKR) against allocated spend</CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis type="number" dataKey="budget" name="Budget" unit=" LKR" fontSize={10} stroke="#888888" />
                        <YAxis type="number" dataKey="roi" name="ROI" unit=" L/Rs" fontSize={10} stroke="#888888" />
                        <ZAxis type="category" dataKey="outlet_id" name="Outlet" />
                        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                        <Scatter name="Outlets" data={m.charts.budget_vs_roi} fill="hsl(var(--primary))" />
                      </ScatterChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>

              {/* Reallocation Centre */}
              <Card className="border-amber-500/20 bg-amber-500/[0.02]">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardTitle className="font-serif text-xl flex items-center gap-1.5">
                      <AlertTriangle className="h-5 w-5 text-amber-500" /> Reallocation Centre
                    </CardTitle>
                    <CardDescription>
                      Review underperforming outlets and shift budgets to high-potential alternatives.
                    </CardDescription>
                  </div>
                  {recs.length > 0 && (
                    <Button 
                      onClick={() => applyReallocations.mutate(currentCampaign.campaign_id)}
                      disabled={applyReallocations.isPending}
                      variant="outline"
                      className="border-amber-500/30 hover:bg-amber-500/10 text-amber-600 gap-1.5"
                    >
                      {applyReallocations.isPending ? "Applying..." : "Apply Recommendations"}
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {recs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-6 text-center">
                      <CheckCircle2 className="h-10 w-10 text-green-500" />
                      <p className="mt-2 text-sm font-medium text-foreground">No budget reallocations needed</p>
                      <p className="text-xs text-muted-foreground mt-0.5 max-w-sm">
                        All pilot outlets are currently meeting performance expectations. Run evaluated snapshots regularly.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="rounded-md border border-amber-500/20 bg-card overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/30">
                              <TableHead>Outlet Name</TableHead>
                              <TableHead className="text-right">Current Spend</TableHead>
                              <TableHead className="text-right">Suggested Spend</TableHead>
                              <TableHead>Reason / Opportunity</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {recs.map((r) => (
                              <TableRow key={r.recommendation_id} className="hover:bg-amber-500/[0.01]">
                                <TableCell className="font-medium">
                                  <div>
                                    <div className="text-sm font-semibold">{r.outlet_name}</div>
                                    <div className="text-[10px] font-mono text-muted-foreground">{r.outlet_id}</div>
                                  </div>
                                </TableCell>
                                <TableCell className="text-right tabular-nums">
                                  {fmtMoney(r.current_budget)}
                                </TableCell>
                                <TableCell className="text-right tabular-nums font-semibold">
                                  <div className="flex items-center justify-end gap-1.5 text-foreground">
                                    <span>{fmtMoney(r.recommended_budget)}</span>
                                    {r.recommended_budget > r.current_budget ? (
                                      <span className="text-[10px] text-green-600 font-bold bg-green-50 px-1 py-0.25 rounded">+ {fmtMoneyCompact(r.recommended_budget - r.current_budget)}</span>
                                    ) : r.recommended_budget < r.current_budget ? (
                                      <span className="text-[10px] text-destructive font-bold bg-red-50 px-1 py-0.25 rounded">- {fmtMoneyCompact(r.current_budget - r.recommended_budget)}</span>
                                    ) : null}
                                  </div>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground max-w-xs leading-relaxed">
                                  {r.recommendation_reason}
                                  {r.expected_improvement > 0 && (
                                    <span className="block font-semibold text-green-600 mt-0.5">
                                      + Expected Improvement: {fmtInt(r.expected_improvement)} L
                                    </span>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Outlet Performance Grid */}
              <Card>
                <CardHeader>
                  <CardTitle className="font-serif text-lg">Outlet Performance & Status Lights</CardTitle>
                  <CardDescription>Track treatment outlets weekly volume progress</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-secondary/40">
                        <TableHead>Outlet ID</TableHead>
                        <TableHead>Outlet Name</TableHead>
                        <TableHead className="text-right">Budget</TableHead>
                        <TableHead className="text-right">Expected Lift</TableHead>
                        <TableHead className="text-right">Actual Lift</TableHead>
                        <TableHead className="text-right">Performance</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                        <TableHead>Notes</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {m.outlets_performance.map((op) => (
                        <TableRow key={op.outlet_id}>
                          <TableCell className="font-mono text-xs">{op.outlet_id}</TableCell>
                          <TableCell className="font-semibold text-sm">{op.outlet_name}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtMoney(op.allocated_budget)}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtInt(op.expected_lift)} L</TableCell>
                          <TableCell className="text-right tabular-nums font-semibold">{fmtInt(op.actual_lift)} L</TableCell>
                          <TableCell className="text-right tabular-nums font-bold text-foreground">{op.performance_pct}%</TableCell>
                          <TableCell className="text-center">
                            <span className={`inline-flex h-2.5 w-2.5 rounded-full ${
                              op.status === "Green" ? "bg-green-500 shadow-green-500/20" :
                              op.status === "Yellow" ? "bg-amber-500 shadow-amber-500/20" :
                              "bg-red-500 shadow-red-500/20 animate-pulse"
                            } shadow-[0_0_8px_currentcolor]`} />
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground max-w-xs leading-normal">{op.notes}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}

          {currentCampaign.status === "Draft" && (
            <div className="flex flex-col items-center justify-center border border-dashed border-border rounded-lg bg-card p-10 text-center">
              <Activity className="h-10 w-10 text-muted-foreground/55 animate-pulse" />
              <h2 className="mt-4 text-base font-semibold">Pilot Campaign Not Active</h2>
              <p className="mt-1 text-sm text-muted-foreground max-w-sm">
                This campaign is currently in Draft. Click "Start Pilot Campaign" to rank target outlets, allocate promotional budget, match controls, and begin simulation.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
