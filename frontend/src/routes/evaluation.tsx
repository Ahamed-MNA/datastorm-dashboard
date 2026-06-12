import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { 
  BarChart3, RefreshCw, Sparkles, TrendingUp, HelpCircle, 
  ArrowRight, ShieldCheck, CheckCircle2, ChevronRight,
  Building2, Calendar, Activity
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtInt, fmtMoney, fmtMoneyCompact, fmtNum, fmtPct } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer 
} from "recharts";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/evaluation")({
  head: () => ({ meta: [{ title: "Pilot Evaluation — Outlet Intelligence" }] }),
  component: EvaluationPage,
});

function EvaluationPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Outlet Detail Modal State
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(null);
  const [selectedOutletType, setSelectedOutletType] = useState<"treatment" | "control">("treatment");

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

  const didEvaluationQuery = useQuery({
    queryKey: ["evaluation-did", activeId],
    queryFn: () => api.getEvaluationDiD(activeId!),
    enabled: !!activeId && activeCampaignQuery.data?.status !== "Draft",
  });

  const outletQuery = useQuery({
    queryKey: ["outlet-detail-eval", selectedOutletId],
    queryFn: () => api.outlet(selectedOutletId!),
    enabled: !!selectedOutletId && detailOpen,
  });

  const outletHistoryQuery = useQuery({
    queryKey: ["outlet-history-eval", selectedOutletId],
    queryFn: () => api.outletHistory(selectedOutletId!),
    enabled: !!selectedOutletId && detailOpen,
  });

  const outletSnapshotsQuery = useQuery({
    queryKey: ["outlet-snapshots-eval", activeId, selectedOutletId],
    queryFn: () => api.getOutletMonitoring(activeId!, selectedOutletId!),
    enabled: !!activeId && !!selectedOutletId && detailOpen && selectedOutletType === "treatment",
  });

  // Mutations
  const runEvaluation = useMutation({
    mutationFn: (id: number) => api.runEvaluationDiD(id),
    onSuccess: () => {
      toast.success("Impact evaluation model re-calculated successfully!");
      queryClient.invalidateQueries({ queryKey: ["evaluation-did", activeId] });
    },
    onError: (err: any) => {
      toast.error("Failed to run evaluation: " + err.message);
    }
  });

  const currentCampaign = activeCampaignQuery.data;
  const evalData = didEvaluationQuery.data;

  // Prepare chart data for DiD visualization
  const getChartData = () => {
    if (!evalData) return [];
    
    // We want a comparison: Pre vs Post for Treatment and Control
    // treatment_pre, treatment_post, control_pre, control_post
    const tPre = evalData.pre_volume;
    const tPost = evalData.pre_volume + evalData.treatment_lift;
    
    // For control group pre/post
    // Let's compute average control pre and post based on pairs
    let cPreSum = 0;
    let cPostSum = 0;
    const pairs = evalData.pairs ?? [];
    if (pairs.length > 0) {
      pairs.forEach(p => {
        cPreSum += p.control_pre;
        cPostSum += p.control_post;
      });
      const cPre = cPreSum / pairs.length;
      const cPost = cPostSum / pairs.length;
      
      return [
        {
          name: "Treatment Group",
          "Pre Volume": roundVal(tPre),
          "Post Volume": roundVal(tPost),
        },
        {
          name: "Control Group",
          "Pre Volume": roundVal(cPre),
          "Post Volume": roundVal(cPost),
        }
      ];
    }
    
    return [
      {
        name: "Treatment Group",
        "Pre Volume": roundVal(tPre),
        "Post Volume": roundVal(tPost),
      },
      {
        name: "Control Group",
        "Pre Volume": roundVal(tPre), // fallback representation
        "Post Volume": roundVal(tPre + evalData.control_lift),
      }
    ];
  };

  const roundVal = (v: number) => Math.round(v * 100) / 100;

  // Resolve confidence badge and level
  const getConfidenceLevel = (score: number) => {
    const s = score * 100;
    if (s >= 95) return { text: "Highly Significant (p < 0.05)", color: "text-green-600 bg-green-50 border-green-200" };
    if (s >= 90) return { text: "Significant (p < 0.10)", color: "text-amber-600 bg-amber-50 border-amber-200" };
    return { text: "Directional / Not Statistically Significant", color: "text-destructive bg-red-50 border-red-200" };
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-serif text-4xl text-foreground">Pilot Evaluation Console</h1>
          <p className="text-sm text-muted-foreground">
            Execute Difference-in-Differences (DiD) evaluations to isolate exact campaign lift against matched control outlets.
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
                {campaignsQuery.data.filter(c => c.status !== "Draft").map((c) => (
                  <SelectItem key={c.campaign_id} value={String(c.campaign_id)}>
                    {c.campaign_name} ({c.status})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {currentCampaign && currentCampaign.status !== "Draft" && (
            <Button 
              onClick={() => runEvaluation.mutate(currentCampaign.campaign_id)}
              disabled={runEvaluation.isPending}
              variant="outline"
              className="gap-1.5 h-9"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${runEvaluation.isPending ? "animate-spin" : ""}`} /> Recalculate Model
            </Button>
          )}
        </div>
      </div>

      {campaignsQuery.data && campaignsQuery.data.filter(c => c.status !== "Draft").length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card p-10 text-center">
          <BarChart3 className="h-12 w-12 text-muted-foreground/60" />
          <h2 className="mt-4 text-lg font-semibold">No Active Pilots Found</h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-sm">
            You must start a pilot campaign first to generate treatment/control matching groups and monitoring data before running impact evaluations.
          </p>
        </div>
      )}

      {currentCampaign && currentCampaign.status !== "Draft" && evalData && (
        <div className="space-y-6 animate-fade-in">
          {/* Campaign Details Subheader */}
          <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
            <h2 className="text-xl font-bold font-serif">{currentCampaign.campaign_name} Evaluation Report</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Province: <span className="font-semibold text-foreground">{currentCampaign.province}</span> &middot; 
              Budget: <span className="font-semibold text-foreground">{fmtMoney(currentCampaign.total_budget)}</span> &middot;
              Evaluation generated: <span className="font-semibold text-foreground">{evalData.generated_at ? new Date(evalData.generated_at).toLocaleString() : "Never"}</span>
            </p>
          </div>

          {/* DiD KPIs */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <KpiCard
              label="Pre Volume (Avg)"
              value={`${fmtNum(evalData.pre_volume)} L`}
              hint="Pre-campaign monthly baseline"
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <KpiCard
              label="Post Volume (Avg)"
              value={`${fmtNum(evalData.pre_volume + evalData.treatment_lift)} L`}
              hint="Post-campaign monthly volume"
              icon={<TrendingUp className="h-4 w-4 text-green-500" />}
            />
            <KpiCard
              label="Treatment Lift (Avg)"
              value={`+ ${fmtNum(evalData.treatment_lift)} L`}
              hint="Gross intervention growth"
              icon={<Sparkles className="h-4 w-4 text-primary" />}
            />
            <KpiCard
              label="Control Lift (Avg)"
              value={`+ ${fmtNum(evalData.control_lift)} L`}
              hint="Non-intervention baseline growth"
              icon={<HelpCircle className="h-4 w-4 text-muted-foreground" />}
            />
            <KpiCard
              label="DiD Net Effect"
              value={`+ ${fmtNum(evalData.did_effect)} L`}
              hint="Net incremental volume lift"
              icon={<Sparkles className="h-4 w-4 text-green-500" />}
              className="border-green-500/30 bg-green-500/[0.03]"
              accent
            />
          </div>

          {/* Chart & econometric detail */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* DiD Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="font-serif text-lg">Econometric DiD Visualizer</CardTitle>
                <CardDescription>Average monthly volume lift (Treatment vs Control matched baseline)</CardDescription>
              </CardHeader>
              <CardContent className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={getChartData()}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                    <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} />
                    <YAxis stroke="#888888" fontSize={11} tickLine={false} unit=" L" />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Pre Volume" fill="#94a3b8" radius={[4, 4, 0, 0]} opacity={0.8} />
                    <Bar dataKey="Post Volume" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* econometric analysis context */}
            <Card className="flex flex-col justify-between">
              <CardHeader>
                <CardTitle className="font-serif text-lg">Statistical Confidence Profile</CardTitle>
                <CardDescription>Econometric modeling statistics and validation check</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6 flex-1">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-muted-foreground">Confidence Score:</span>
                    <span className="font-bold text-foreground font-mono">{fmtPct(evalData.confidence_score, 1)}</span>
                  </div>
                  <Progress value={evalData.confidence_score * 100} className="h-2.5" />
                  <div className={`mt-2 rounded-md border p-3 text-xs font-semibold ${getConfidenceLevel(evalData.confidence_score).color}`}>
                    {getConfidenceLevel(evalData.confidence_score).text}
                  </div>
                </div>

                <div className="rounded-lg bg-secondary/35 p-4 space-y-3 text-xs leading-relaxed text-muted-foreground">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <ShieldCheck className="h-4 w-4 text-green-500" />
                    Difference-in-Differences (DiD) Logic
                  </div>
                  <p>
                    Difference-in-Differences is a statistical technique that mimics an experimental design. 
                    By comparing the change in the treatment group with the change in the control group:
                  </p>
                  <code className="block rounded bg-card p-2 text-center font-mono font-bold text-foreground border border-border">
                    DiD = (Treatment_Post - Treatment_Pre) - (Control_Post - Control_Pre)
                  </code>
                  <p>
                    This filters out temporal noise (seasonal fluctuations, distributor holidays, economic updates) 
                    and isolates the **true, incremental impact** attributable directly to your budget allocation.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Matched Pairs Detail Grid */}
          <Card>
            <CardHeader>
              <CardTitle className="font-serif text-lg">Matched Outlets Pre/Post Detail Pairs</CardTitle>
              <CardDescription>
                Compare each treatment pilot outlet with its nearest-neighbor matched control counterpart.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-secondary/40">
                    <TableHead colSpan={4} className="border-r border-border text-center bg-primary/[0.02] text-primary font-bold">Treatment Group (Active Pilot)</TableHead>
                    <TableHead colSpan={3} className="border-r border-border text-center bg-muted/20 text-muted-foreground font-bold">Matched Control Group</TableHead>
                    <TableHead className="text-center bg-green-500/[0.02] text-green-600 font-bold">Incremental</TableHead>
                  </TableRow>
                  <TableRow className="bg-secondary/15">
                    <TableHead>Outlet Name</TableHead>
                    <TableHead className="text-right">Pre (3M Avg)</TableHead>
                    <TableHead className="text-right">Post (Snap)</TableHead>
                    <TableHead className="text-right border-r border-border font-bold">Lift</TableHead>
                    <TableHead>Matched Control</TableHead>
                    <TableHead className="text-right">Pre (3M Avg)</TableHead>
                    <TableHead className="text-right border-r border-border">Post (Snap)</TableHead>
                    <TableHead className="text-right font-bold text-green-600">Net Volume Lift</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {evalData.pairs.map((p) => (
                    <TableRow key={p.treatment_id}>
                      <TableCell className="font-medium">
                        <div 
                          className="cursor-pointer hover:bg-muted/50 p-1.5 rounded transition-colors group"
                          onClick={() => {
                            setSelectedOutletId(p.treatment_id);
                            setSelectedOutletType("treatment");
                            setDetailOpen(true);
                          }}
                        >
                          <div className="text-sm font-semibold text-primary group-hover:underline flex items-center gap-1">
                            {p.treatment_name}
                            <ChevronRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                          </div>
                          <div className="text-[10px] font-mono text-muted-foreground">{p.treatment_id} &middot; {p.treatment_type} &middot; {p.treatment_size}</div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{fmtNum(p.treatment_pre)} L</TableCell>
                      <TableCell className="text-right tabular-nums">{fmtNum(p.treatment_post)} L</TableCell>
                      <TableCell className="text-right tabular-nums border-r border-border font-bold text-primary">
                        + {fmtNum(p.treatment_lift)} L
                      </TableCell>
                      <TableCell>
                        <div 
                          className="cursor-pointer hover:bg-muted/50 p-1.5 rounded transition-colors group"
                          onClick={() => {
                            setSelectedOutletId(p.control_id);
                            setSelectedOutletType("control");
                            setDetailOpen(true);
                          }}
                        >
                          <div className="text-sm font-semibold text-primary group-hover:underline flex items-center gap-1">
                            {p.control_name}
                            <ChevronRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                          </div>
                          <div className="text-[10px] font-mono text-muted-foreground">{p.control_id}</div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{fmtNum(p.control_pre)} L</TableCell>
                      <TableCell className="text-right tabular-nums border-r border-border">{fmtNum(p.control_post)} L</TableCell>
                      <TableCell className="text-right tabular-nums font-bold text-green-600 bg-green-500/[0.01]">
                        {p.net_lift >= 0 ? "+" : ""} {fmtNum(p.net_lift)} L
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Outlet Details Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-serif text-xl">
              Outlet Details: {outletQuery.data?.Outlet_Name || "Loading..."}
            </DialogTitle>
            <DialogDescription>
              View profile baseline, historical sales, and pilot performance for {selectedOutletId}.
            </DialogDescription>
          </DialogHeader>

          {outletQuery.isLoading ? (
            <div className="flex h-60 items-center justify-center">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : outletQuery.data ? (
            (() => {
              const o = outletQuery.data;
              const snapshotChartData = (outletSnapshotsQuery.data || []).map((s, idx) => ({
                week: `Week ${idx + 1}`,
                volume: s.actual_volume,
                revenue: s.actual_revenue,
                lift: s.actual_lift,
              }));

              return (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                  {/* Left Column: General Profile & History */}
                  <div className="space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-primary" />
                          General Profile
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Distributor:</span>
                          <span className="font-semibold">{o.Distributor}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Province:</span>
                          <span className="font-semibold">{o.Province}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Outlet Type:</span>
                          <span className="font-semibold">{o.Outlet_Type}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Outlet Size:</span>
                          <span className="font-semibold">{o.Outlet_Size}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Cooler Count:</span>
                          <span className="font-semibold">{o.Cooler_Count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Location:</span>
                          <span className="font-semibold font-mono">{o.Latitude.toFixed(5)}, {o.Longitude.toFixed(5)}</span>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-primary" />
                          Historical Sales (Last 3 Months)
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-0 max-h-40 overflow-y-auto">
                        {outletHistoryQuery.data && outletHistoryQuery.data.length > 0 ? (
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-secondary/20 text-[10px]">
                                <TableHead>Period</TableHead>
                                <TableHead className="text-right">Volume (Liters)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody className="text-[11px]">
                              {outletHistoryQuery.data.slice(-3).map((h, i) => (
                                <TableRow key={i}>
                                  <TableCell>{h.Year} - Month {h.Month}</TableCell>
                                  <TableCell className="text-right font-mono">{fmtNum(h.Volume_Liters)} L</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        ) : (
                          <p className="p-4 text-xs text-muted-foreground text-center">No historical sales found.</p>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Right Column: Campaign Performance & Snapshots */}
                  <div className="space-y-4">
                    <Card className={selectedOutletType === "treatment" ? "border-primary/20 bg-primary/[0.01]" : ""}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Activity className="h-4 w-4 text-primary" />
                          {selectedOutletType === "treatment" ? "Treatment Group Performance" : "Control Group Performance"}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2 text-xs">
                        {selectedOutletType === "treatment" && o.budget_allocation && (
                          <>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground font-semibold text-primary">Allocated Budget:</span>
                              <span className="font-bold text-primary">{fmtMoney(o.budget_allocation.Allocated_Budget)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Expected Lift:</span>
                              <span className="font-semibold">{fmtNum(o.budget_allocation.Expected_Lift)} L</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Expected ROI:</span>
                              <span className="font-semibold">{fmtPct(o.budget_allocation.ROI)}</span>
                            </div>
                          </>
                        )}
                        {(() => {
                          const pair = evalData?.pairs.find(p => p.treatment_id === o.Outlet_ID || p.control_id === o.Outlet_ID);
                          if (pair) {
                            const pre = selectedOutletType === "treatment" ? pair.treatment_pre : pair.control_pre;
                            const post = selectedOutletType === "treatment" ? pair.treatment_post : pair.control_post;
                            const lift = selectedOutletType === "treatment" ? pair.treatment_lift : pair.control_lift;
                            return (
                              <>
                                <div className="flex justify-between border-t border-border/60 pt-2 mt-2">
                                  <span className="text-muted-foreground">Pre-Campaign Baseline (Avg):</span>
                                  <span className="font-semibold">{fmtNum(pre)} L</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Post-Campaign Volume:</span>
                                  <span className="font-semibold">{fmtNum(post)} L</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground font-semibold">Net Growth Lift:</span>
                                  <span className="font-bold text-green-600">+{fmtNum(lift)} L</span>
                                </div>
                              </>
                            );
                          }
                          return null;
                        })()}
                      </CardContent>
                    </Card>

                    {selectedOutletType === "treatment" && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            Weekly Pilot Snaps (Volume)
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="h-40 pb-2">
                          {outletSnapshotsQuery.isLoading ? (
                            <div className="flex h-full items-center justify-center">
                              <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                            </div>
                          ) : outletSnapshotsQuery.data && outletSnapshotsQuery.data.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={snapshotChartData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                                <XAxis dataKey="week" stroke="#888888" fontSize={9} tickLine={false} />
                                <YAxis stroke="#888888" fontSize={9} tickLine={false} unit=" L" />
                                <Tooltip wrapperStyle={{ fontSize: 10 }} />
                                <Bar dataKey="volume" fill="hsl(var(--primary))" name="Vol (L)" radius={[2, 2, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          ) : (
                            <p className="text-xs text-muted-foreground text-center pt-8">No snapshots found.</p>
                          )}
                        </CardContent>
                      </Card>
                    )}

                    {selectedOutletType === "control" && (
                      <div className="rounded-lg bg-muted/30 border border-border p-4 text-xs text-muted-foreground leading-relaxed">
                        <p className="font-semibold text-foreground mb-1">Matched Control Outlet Context</p>
                        Control outlets are matched to treatment outlets in the same province, size, and category. 
                        They do not receive any budget allocations or campaign funding, and are monitored solely as a baseline to isolate external factors like seasonality.
                      </div>
                    )}
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="text-xs text-destructive p-4">Failed to load outlet details.</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
