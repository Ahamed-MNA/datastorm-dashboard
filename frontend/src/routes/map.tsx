import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";

import { api, type MapOutletItem, type HeatmapItem } from "@/lib/api";
import { fmtInt } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/map")({
  head: () => ({ meta: [{ title: "Map — Outlet Intelligence" }] }),
  component: MapPage,
});

function MapPage() {
  const outlets = useQuery({ queryKey: ["map-outlets"], queryFn: api.mapOutlets });
  const heat = useQuery({ queryKey: ["map-heatmap"], queryFn: api.mapHeatmap });
  const pois = useQuery({ queryKey: ["map-pois"], queryFn: api.mapPois });

  const [showOutlets, setShowOutlets] = useState(true);
  const [showHeat, setShowHeat] = useState(true);
  const [showPois, setShowPois] = useState(false);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="font-serif text-4xl text-foreground">Geospatial View</h1>
        <p className="text-sm text-muted-foreground">
          Visualise outlet density, opportunity hotspots and points-of-interest gravity across the
          territory.
        </p>
      </div>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Layers className="h-4 w-4" /> Layers
            </div>
            <LayerToggle id="outlets" checked={showOutlets} onChange={setShowOutlets} label="Outlets" />
            <LayerToggle id="heat" checked={showHeat} onChange={setShowHeat} label="Opportunity heatmap" />
            <LayerToggle id="pois" checked={showPois} onChange={setShowPois} label="POI gravity" />
            <div className="ml-auto text-xs text-muted-foreground">
              {outlets.data ? `${fmtInt(outlets.data.length)} outlets` : "Loading…"}
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="overflow-hidden">
        <div className="h-[calc(100vh-280px)] min-h-[480px] w-full">
          <LeafletMap
            outlets={showOutlets ? outlets.data ?? [] : []}
            heat={showHeat ? heat.data ?? [] : []}
            pois={showPois ? pois.data ?? [] : []}
          />
        </div>
      </Card>
    </div>
  );
}

function LayerToggle({
  id,
  checked,
  onChange,
  label,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
      <Label htmlFor={id} className="text-sm">
        {label}
      </Label>
    </div>
  );
}

function LeafletMap({
  outlets,
  heat,
  pois,
}: {
  outlets: MapOutletItem[];
  heat: HeatmapItem[];
  pois: { Latitude: number; Longitude: number; POI_Total_Impact_Score: number }[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const layersRef = useRef<{ outlets?: any; heat?: any; pois?: any }>({});
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !containerRef.current) return;
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet.heat");
      if (cancelled || !containerRef.current) return;
      if (mapRef.current) return;
      const map = L.map(containerRef.current).setView([7.5, 80.7], 8);
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
  }, []);

  useEffect(() => {
    if (!ready) return;
    (async () => {
      const L = (await import("leaflet")).default;
      const map = mapRef.current;
      if (!map) return;

      // outlets
      if (layersRef.current.outlets) {
        map.removeLayer(layersRef.current.outlets);
        layersRef.current.outlets = undefined;
      }
      if (outlets.length) {
        const group = L.layerGroup();
        for (const o of outlets) {
          const r = Math.max(3, Math.min(9, Math.log10(Math.max(10, o.Predicted_Potential)) * 2.2));
          const marker = L.circleMarker([o.Latitude, o.Longitude], {
            radius: r,
            color: "#064e3b",
            weight: 1,
            fillColor: "#0d7a5f",
            fillOpacity: 0.7,
          }).bindPopup(
            `<div style="font-family: Inter, sans-serif; font-size: 12px;">
              <div style="font-weight:600;">${o.Outlet_Name}</div>
              <div style="color:#666;">${o.Province} · ${o.Distributor}</div>
              <div style="margin-top:4px;">Potential: <b>${fmtInt(o.Predicted_Potential)} L</b></div>
              <a href="/outlets/${o.Outlet_ID}" style="color:#064e3b;font-weight:600;">View details →</a>
            </div>`,
          );
          group.addLayer(marker);
        }
        group.addTo(map);
        layersRef.current.outlets = group;
      }

      // heatmap
      if (layersRef.current.heat) {
        map.removeLayer(layersRef.current.heat);
        layersRef.current.heat = undefined;
      }
      if (heat.length) {
        const maxGap = Math.max(...heat.map((h) => h.Opportunity_Gap), 1);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const pts: any = heat.map((h) => [h.Latitude, h.Longitude, h.Opportunity_Gap / maxGap]);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const heatLayer = (L as any).heatLayer(pts, {
          radius: 18,
          blur: 22,
          maxZoom: 12,
          gradient: { 0.2: "#0d7a5f", 0.4: "#c9a84c", 0.7: "#d97706", 1.0: "#7c2d12" },
        });
        heatLayer.addTo(map);
        layersRef.current.heat = heatLayer;
      }

      // pois
      if (layersRef.current.pois) {
        map.removeLayer(layersRef.current.pois);
        layersRef.current.pois = undefined;
      }
      if (pois.length) {
        const max = Math.max(...pois.map((p) => p.POI_Total_Impact_Score), 1);
        const group = L.layerGroup();
        for (const p of pois) {
          const r = 3 + (p.POI_Total_Impact_Score / max) * 12;
          group.addLayer(
            L.circleMarker([p.Latitude, p.Longitude], {
              radius: r,
              color: "#c9a84c",
              weight: 0,
              fillColor: "#c9a84c",
              fillOpacity: 0.35,
            }),
          );
        }
        group.addTo(map);
        layersRef.current.pois = group;
      }
    })();
  }, [outlets, heat, pois, ready]);

  return <div ref={containerRef} className="h-full w-full" />;
}
