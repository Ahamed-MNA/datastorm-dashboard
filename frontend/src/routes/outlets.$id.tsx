import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MapPin, Sparkles, Target, TrendingUp, Gauge, Zap } from "lucide-react";
import { useEffect, useRef, useState, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";

import { api } from "@/lib/api";
import { fmtInt, fmtNum, fmtPctRaw, fmtMoneyCompact } from "@/lib/format";
import { KpiCard } from "@/components/kpi-card";
import { MetricTooltip } from "@/components/metric-tooltip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/outlets/$id")({
  head: ({ params }) => ({
    meta: [{ title: `${params.id} — Outlet Intelligence` }],
  }),
  component: OutletDetail,
});

function OutletDetail() {
  const { id } = Route.useParams();
  const outlet = useQuery({ queryKey: ["outlet", id], queryFn: () => api.outlet(id) });
  const history = useQuery({ queryKey: ["outlet-history", id], queryFn: () => api.outletHistory(id) });
  const xai = useQuery({ queryKey: ["xai", id], queryFn: () => api.xai(id), retry: false });

  const o = outlet.data;
  const p = o?.prediction;

  // Fetch competitors linked to this outlet's territory
  const competitorsQuery = useQuery({
    queryKey: ["map-competitors", o?.Province, o?.Distributor],
    queryFn: () => api.mapCompetitors({ province: o?.Province, distributor: o?.Distributor }),
    enabled: !!o,
  });

  const competitorLinks = useMemo(() => {
    if (!competitorsQuery.data || !o) return [];
    return competitorsQuery.data.filter(
      (link) => link.Source_Outlet_ID === o.Outlet_ID || link.Target_Outlet_ID === o.Outlet_ID
    );
  }, [competitorsQuery.data, o]);

  const isLoading = outlet.isLoading || xai.isLoading;

  // Section A: Historical Monthly Performance (Baseline)
  const salesVal = xai.data ? xai.data.actual_volume : (p ? p.Historical_Sales : 0);
  const potentialVal = xai.data ? xai.data.predicted_potential : (p && p.Efficiency_Score > 0 ? p.Historical_Sales / p.Efficiency_Score : 0);
  const efficiencyVal = xai.data ? xai.data.efficiency_score : (p ? p.Efficiency_Score : 0);

  // Section B: Peak Season Target (January 2026 Target)
  const peakPotential = p ? p.Predicted_Potential : 0;
  const peakGap = p ? p.Opportunity_Gap : 0;
  const peakGrowth = p ? p.Growth_Percent : 0;
  const peakCapture = peakPotential > 0 ? (salesVal / peakPotential) * 100 : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit gap-2">
        <Link to="/outlets">
          <ArrowLeft className="h-4 w-4" /> Back to Outlets
        </Link>
      </Button>

      {outlet.isLoading && <Skeleton className="h-24 w-full" />}
      {o && (
        <Card className="overflow-hidden border-border/60 shadow">
          <div className="h-1.5 bg-gradient-to-r from-primary via-accent to-primary" />
          <CardContent className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  {o.Outlet_ID}
                </div>
                <h1 className="font-serif text-4xl text-foreground">{o.Outlet_Name}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  <Badge variant="outline" className="gap-1">
                    <MapPin className="h-3 w-3" /> {o.Province}
                  </Badge>
                  <Badge variant="outline">{o.Distributor}</Badge>
                  <Badge variant="secondary">{o.Outlet_Type}</Badge>
                  <Badge variant="secondary">{o.Outlet_Size}</Badge>
                  <span className="text-muted-foreground">· {o.Cooler_Count} coolers</span>
                  <span className="text-muted-foreground">
                    · {o.Latitude.toFixed(4)}, {o.Longitude.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-5 w-64" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-5 w-64" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          </div>
        </div>
      ) : (
        p && (
          <div className="space-y-6">
            {/* Section A: Historical Monthly Performance */}
            <div className="space-y-2.5">
              <h2 className="font-serif text-lg font-semibold text-muted-foreground uppercase tracking-wide">
                Historical Monthly Performance (Baseline)
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <KpiCard
                  label="Historical Sales"
                  term="Historical Sales"
                  value={`${fmtInt(salesVal)} L`}
                  hint="Volume actually sold in latest recorded month"
                  icon={<TrendingUp className="h-4 w-4" />}
                  progress={potentialVal > 0 ? (salesVal / potentialVal) * 100 : 0}
                  progressColor="bg-sky-500"
                />
                <KpiCard
                  label="Frontier Potential"
                  term="Predicted Potential"
                  value={`${fmtInt(potentialVal)} L`}
                  hint="Expected baseline ceiling for this outlet size/type"
                  icon={<Target className="h-4 w-4" />}
                  accent
                  progress={100}
                  progressColor="bg-emerald-500"
                />
                <KpiCard
                  label="Frontier Efficiency"
                  term="Efficiency Score"
                  value={fmtPctRaw(efficiencyVal * 100)}
                  hint={EfficiencyHint(efficiencyVal)}
                  icon={<Gauge className="h-4 w-4" />}
                  progress={efficiencyVal * 100}
                  progressColor={
                    efficiencyVal >= 0.7
                      ? "bg-emerald-500"
                      : efficiencyVal >= 0.4
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }
                />
              </div>
            </div>

            {/* Section B: Peak Season Target */}
            <div className="space-y-2.5">
              <h2 className="font-serif text-lg font-semibold text-muted-foreground uppercase tracking-wide">
                Peak Season Target (January 2026 Opportunity)
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <KpiCard
                  label="Uncapped Peak Potential"
                  value={`${fmtInt(peakPotential)} L`}
                  hint="January ceiling if supply constraints are cleared"
                  icon={<Sparkles className="h-4 w-4" />}
                  accent
                  progress={100}
                  progressColor="bg-indigo-500"
                />
                <KpiCard
                  label="Peak Opportunity Gap"
                  term="Opportunity Gap"
                  value={`${fmtInt(peakGap)} L`}
                  hint={`Current Peak Capacity Capture: ${fmtPctRaw(peakCapture)}`}
                  icon={<Target className="h-4 w-4" />}
                  progress={peakCapture}
                  progressColor="bg-amber-500"
                />
                <KpiCard
                  label="Peak Growth Runway"
                  term="Growth %"
                  value={fmtPctRaw(peakGrowth)}
                  hint="Expansion potential compared to actual baseline"
                  icon={<TrendingUp className="h-4 w-4" />}
                  progress={Math.min(100, peakGrowth)}
                  progressColor="bg-sky-500"
                />
              </div>
            </div>
          </div>
        )
      )}

      {/* XAI explanation */}
      <Card className="shadow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-serif text-2xl">
            <Zap className="h-5 w-5 text-accent" /> Why This Score
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {xai.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-11/12" />
              <Skeleton className="h-4 w-10/12" />
            </div>
          )}
          {xai.isError && (
            <p className="text-sm text-muted-foreground">
              The AI explanation could not be generated right now. The numbers above still tell the
              core story.
            </p>
          )}
          {xai.data && (
            <>
              <div className="prose prose-sm max-w-none whitespace-pre-line text-foreground/90 leading-relaxed">
                {xai.data.explanation}
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 pt-4 border-t">
                <div>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    Top drivers of the score
                  </h3>
                  <DriversChart drivers={xai.data.payload.top_drivers ?? []} />
                </div>
                <div className="space-y-3">
                  <div>
                    <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Local signals
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(xai.data.payload.local_signals ?? {}).map(([k, v]) => (
                        <SignalChip key={k} label={k} value={v} />
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Operational constraints
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(xai.data.payload.operational_constraints ?? {}).map(([k, v]) => (
                        <SignalChip key={k} label={k} value={v} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="shadow">
          <CardHeader>
            <CardTitle className="font-serif text-2xl">3-Year Sales History</CardTitle>
            <p className="text-xs text-muted-foreground">Monthly volume sold (Liters) vs Total Bill Value (LKR).</p>
          </CardHeader>
          <CardContent>
            <HistoryChart data={history.data ?? []} />
          </CardContent>
        </Card>
        <Card className="shadow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-serif text-2xl">
              Neighborhood Footprint
              <MetricTooltip term="POI Impact" />
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Pull strength from nearby points of interest (schools, religious sites, transit, etc.).
            </p>
          </CardHeader>
          <CardContent>
            {o && <SpatialRadar spatial={o.spatial_features as unknown as Record<string, number>} />}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card className="shadow">
          <CardHeader>
            <CardTitle className="font-serif text-2xl">Nearby Competitors Map</CardTitle>
            <p className="text-xs text-muted-foreground">
              Geospatial layout centered on {o?.Outlet_Name ?? "Outlet"} displaying competitive linkages and distance/friction indexes.
            </p>
          </CardHeader>
          <CardContent className="h-[400px]">
            {o && (
              <CompetitorMap
                centerLat={o.Latitude}
                centerLon={o.Longitude}
                outletName={o.Outlet_Name}
                outletId={o.Outlet_ID}
                competitorLinks={competitorLinks}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function EfficiencyHint(score: number) {
  if (score >= 0.7) return "Operating near full potential";
  if (score >= 0.4) return "Moderate headroom for growth";
  return "Significant unrealised potential";
}

function DriversChart({ drivers }: { drivers: { feature_name: string; percentage_impact: number }[] }) {
  const data = [...drivers]
    .sort((a, b) => Math.abs(b.percentage_impact) - Math.abs(a.percentage_impact))
    .slice(0, 8)
    .map((d) => ({
      name: d.feature_name.replace(/_/g, " "),
      impact: d.percentage_impact,
    }));
  if (data.length === 0) return <p className="text-sm text-muted-foreground">No drivers available.</p>;
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 8, left: 100, bottom: 4 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" tickFormatter={(v) => `${v.toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" width={140} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any) => [`${v.toFixed(2)}%`, "Impact"]}
        />
        <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.impact >= 0 ? "#10b981" : "#ef4444"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function SignalChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-2.5 py-1 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-semibold text-foreground">{fmtNum(value, 2)}</span>
    </div>
  );
}

function HistoryChart({ data }: { data: { Year: number; Month: number; Volume_Liters: number; Total_Bill_Value: number }[] }) {
  const series = [...data]
    .sort((a, b) => {
      if (a.Year !== b.Year) return a.Year - b.Year;
      return a.Month - b.Month;
    })
    .map((d) => ({
      label: `${d.Year}-${String(d.Month).padStart(2, "0")}`,
      volume: d.Volume_Liters,
      billValue: d.Total_Bill_Value,
    }));

  if (series.length === 0) return <p className="text-sm text-muted-foreground">No history available.</p>;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" />
        <YAxis yAxisId="left" tick={{ fontSize: 11 }} stroke="var(--primary)" tickFormatter={(v) => fmtInt(v)} />
        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} stroke="var(--accent)" tickFormatter={(v) => fmtMoneyCompact(v)} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any, name: any) => {
            if (name === "Volume") return [`${fmtInt(v)} L`, "Volume"];
            return [`${fmtMoneyCompact(v)}`, "Bill Value"];
          }}
        />
        <Line yAxisId="left" type="monotone" name="Volume" dataKey="volume" stroke="var(--primary)" strokeWidth={2} dot={false} />
        <Line yAxisId="right" type="monotone" name="Bill Value" dataKey="billValue" stroke="var(--accent)" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Keep original SpatialRadar implementation
function SpatialRadar({ spatial }: { spatial: { [k: string]: number } }) {
  const keys = ["School_Gravity", "Hospital_Gravity", "Transit_Gravity", "Religious_Gravity", "Commercial_Gravity", "Residential_Gravity", "Tourism_Gravity"];
  const max = Math.max(1, ...keys.map((k) => spatial[k] ?? 0));
  const data = keys.map((k) => ({
    feature: k.replace("_Gravity", ""),
    value: (spatial[k] ?? 0) / max,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data}>
        <PolarGrid stroke="var(--border)" />
        <PolarAngleAxis dataKey="feature" tick={{ fontSize: 11 }} />
        <Radar dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.35} />
        <RTooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", fontSize: 12 }}
          formatter={(v: any) => [fmtPctRaw(v * 100, 0), "Relative pull"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// Keep original CompetitorMap implementation
function CompetitorMap({
  centerLat,
  centerLon,
  outletName,
  outletId,
  competitorLinks,
}: {
  centerLat: number;
  centerLon: number;
  outletName: string;
  outletId: string;
  competitorLinks: {
    Source_Outlet_ID: string;
    Source_Lat: number;
    Source_Lon: number;
    Target_Outlet_ID: string;
    Target_Lat: number;
    Target_Lon: number;
    Distance_Meters: number;
    Competitive_Friction: number;
  }[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const layersRef = useRef<{ markers?: any; lines?: any }>({});
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !containerRef.current) return;
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !containerRef.current) return;
      if (mapRef.current) return;

      const map = L.map(containerRef.current).setView([centerLat, centerLon], 13);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 18,
      }).addTo(map);

      mapRef.current = map;
      setReady(true);
    })();
    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [centerLat, centerLon]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    (async () => {
      const L = (await import("leaflet")).default;
      const map = mapRef.current;

      // Clear previous layers
      if (layersRef.current.markers) {
        map.removeLayer(layersRef.current.markers);
      }
      if (layersRef.current.lines) {
        map.removeLayer(layersRef.current.lines);
      }

      const markersGroup = L.layerGroup();
      const linesGroup = L.layerGroup();

      // Main outlet marker (prominent blue)
      const mainMarker = L.circleMarker([centerLat, centerLon], {
        radius: 9,
        color: "#1e3a8a",
        weight: 2,
        fillColor: "#3b82f6",
        fillOpacity: 0.9,
      }).bindPopup(
        `<div style="font-family: Inter, sans-serif; font-size: 12px; width: 150px;">
          <div style="font-weight:600; color:#1e3a8a;">${outletName}</div>
          <div style="color:#666;">Outlet ID: ${outletId}</div>
          <div style="margin-top:2px; font-weight:600; color:#0d7a5f;">Subject Outlet</div>
        </div>`
      );
      markersGroup.addLayer(mainMarker);

      // Plot competitors and lines
      const plottedCompetitors = new Set<string>();

      for (const link of competitorLinks) {
        const isSource = link.Source_Outlet_ID === outletId;
        const competitorId = isSource ? link.Target_Outlet_ID : link.Source_Outlet_ID;
        const compLat = isSource ? link.Target_Lat : link.Source_Lat;
        const compLon = isSource ? link.Target_Lon : link.Source_Lon;

        // Plot competitor marker if not done already
        if (!plottedCompetitors.has(competitorId)) {
          plottedCompetitors.add(competitorId);
          const compMarker = L.circleMarker([compLat, compLon], {
            radius: 6,
            color: "#b91c1c",
            weight: 1,
            fillColor: "#ef4444",
            fillOpacity: 0.8,
          }).bindPopup(
            `<div style="font-family: Inter, sans-serif; font-size: 12px; width: 180px;">
              <div style="font-weight:600; color:#b91c1c;">Competitor Outlet</div>
              <div style="color:#666;">Outlet ID: ${competitorId}</div>
              <div style="margin-top:4px; font-size: 11px;">
                Distance: <b>${fmtInt(link.Distance_Meters)} m</b><br/>
                Friction Index: <b>${link.Competitive_Friction.toFixed(3)}</b>
              </div>
              <a href="/outlets/${competitorId}" style="color:#2563eb; font-weight:600; text-decoration:none; display:inline-block; margin-top:4px;">View details →</a>
            </div>`
          );
          markersGroup.addLayer(compMarker);
        }

        // Draw connecting line
        const polyline = L.polyline(
          [
            [centerLat, centerLon],
            [compLat, compLon],
          ],
          {
            color: "#f59e0b",
            weight: 1.5,
            opacity: 0.6,
            dashArray: "4,4",
          }
        ).bindPopup(
          `<div style="font-family: Inter, sans-serif; font-size: 11px;">
            <b>Competition Link</b><br/>
            Distance: ${fmtInt(link.Distance_Meters)} meters<br/>
            Friction Impact: ${link.Competitive_Friction.toFixed(3)}
          </div>`
        );
        linesGroup.addLayer(polyline);
      }

      linesGroup.addTo(map);
      markersGroup.addTo(map);

      layersRef.current.markers = markersGroup;
      layersRef.current.lines = linesGroup;

      // Adjust map bounds to fit all competitors
      if (plottedCompetitors.size > 0) {
        const bounds = L.latLngBounds([[centerLat, centerLon]]);
        for (const link of competitorLinks) {
          const isSource = link.Source_Outlet_ID === outletId;
          const compLat = isSource ? link.Target_Lat : link.Source_Lat;
          const compLon = isSource ? link.Target_Lon : link.Source_Lon;
          bounds.extend([compLat, compLon]);
        }
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    })();
  }, [ready, competitorLinks, centerLat, centerLon, outletName, outletId]);

  return <div ref={containerRef} className="h-full w-full rounded-md border" />;
}
