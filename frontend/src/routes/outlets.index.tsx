import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { zodValidator, fallback } from "@tanstack/zod-adapter";
import { z } from "zod";
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Search } from "lucide-react";
import { useMemo, useState, useEffect } from "react";

import { api } from "@/lib/api";
import { fmtInt } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PAGE_SIZE = 25;

const searchSchema = z.object({
  page: fallback(z.number().int().min(1), 1).default(1),
  province: fallback(z.string(), "").default(""),
  distributor: fallback(z.string(), "").default(""),
  q: fallback(z.string(), "").default(""),
  sort_by: fallback(z.string(), "Outlet_ID").default("Outlet_ID"),
  sort_order: fallback(z.enum(["asc", "desc"]), "asc").default("asc"),
});

export const Route = createFileRoute("/outlets/")({
  validateSearch: zodValidator(searchSchema),
  head: () => ({ meta: [{ title: "Outlets — Outlet Intelligence" }] }),
  component: OutletsPage,
});

function OutletsPage() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });

  const skip = (search.page - 1) * PAGE_SIZE;

  const list = useQuery({
    queryKey: ["outlets", search.page, search.province, search.distributor, search.q, search.sort_by, search.sort_order],
    queryFn: () =>
      api.outlets({
        skip,
        limit: PAGE_SIZE,
        province: search.province || undefined,
        distributor: search.distributor || undefined,
        search: search.q || undefined,
        sort_by: search.sort_by,
        sort_order: search.sort_order,
      }),
  });

  const provinces = useQuery({ queryKey: ["dash-prov"], queryFn: api.dashboardProvinces });
  const distributors = useQuery({ queryKey: ["dash-dist"], queryFn: api.dashboardDistributors });

  const [searchInput, setSearchInput] = useState(search.q);
  useEffect(() => setSearchInput(search.q), [search.q]);

  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1;

  const setSearch = (patch: Partial<typeof search>) =>
    navigate({ search: (prev: typeof search) => ({ ...prev, ...patch, page: patch.page ?? 1 }) });

  const toggleSort = (col: string) => {
    if (search.sort_by === col) {
      setSearch({ sort_order: search.sort_order === "asc" ? "desc" : "asc", page: search.page });
    } else {
      setSearch({ sort_by: col, sort_order: "asc" });
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-6">
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <h1 className="font-serif text-4xl text-foreground">Outlet Explorer</h1>
          <p className="text-sm text-muted-foreground">
            Browse every outlet, filter by territory, and drill in for predicted potential.
          </p>
        </div>
        <Button asChild variant="outline" className="gap-2">
          <a href={api.outletExportUrl()} target="_blank" rel="noreferrer">
            <Download className="h-4 w-4" /> Export CSV
          </a>
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <form
              className="relative flex-1 min-w-[220px]"
              onSubmit={(e) => {
                e.preventDefault();
                setSearch({ q: searchInput });
              }}
            >
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by Outlet ID or name…"
                className="pl-9"
              />
            </form>
            <FilterSelect
              label="Province"
              value={search.province}
              onChange={(v) => setSearch({ province: v })}
              options={(provinces.data ?? []).map((p) => p.name)}
            />
            <FilterSelect
              label="Distributor"
              value={search.distributor}
              onChange={(v) => setSearch({ distributor: v })}
              options={(distributors.data ?? []).map((d) => d.name)}
            />
            {(search.province || search.distributor || search.q) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchInput("");
                  setSearch({ province: "", distributor: "", q: "" });
                }}
              >
                Clear
              </Button>
            )}
            <div className="ml-auto text-sm text-muted-foreground">
              {list.data ? `${fmtInt(list.data.total)} outlets` : "Loading…"}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-secondary/40">
                <SortableHead label="Outlet" col="Outlet_ID" sort={search.sort_by} order={search.sort_order} onClick={toggleSort} />
                <TableHead>Province</TableHead>
                <TableHead>Distributor</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Size</TableHead>
                <TableHead className="text-right">Coolers</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading && (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                    Loading outlets…
                  </TableCell>
                </TableRow>
              )}
              {list.data?.items.map((o) => (
                <TableRow key={o.Outlet_ID} className="hover:bg-secondary/30">
                  <TableCell className="font-mono text-xs">
                    <div className="font-semibold">{o.Outlet_ID}</div>
                    <div className="text-muted-foreground">{o.Outlet_Name}</div>
                  </TableCell>
                  <TableCell>{o.Province}</TableCell>
                  <TableCell className="font-mono text-xs">{o.Distributor}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{o.Outlet_Type}</Badge>
                  </TableCell>
                  <TableCell>
                    <SizeBadge size={o.Outlet_Size} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{o.Cooler_Count}</TableCell>
                  <TableCell className="text-right">
                    <Button asChild size="sm" variant="ghost">
                      <Link to="/outlets/$id" params={{ id: o.Outlet_ID }}>
                        View →
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {list.data && list.data.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                    No outlets match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          Page {search.page} of {totalPages}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={search.page <= 1}
            onClick={() => setSearch({ page: search.page - 1 })}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={search.page >= totalPages}
            onClick={() => setSearch({ page: search.page + 1 })}
          >
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function SortableHead({
  label,
  col,
  sort,
  order,
  onClick,
}: {
  label: string;
  col: string;
  sort: string;
  order: "asc" | "desc";
  onClick: (c: string) => void;
}) {
  const active = sort === col;
  return (
    <TableHead>
      <button onClick={() => onClick(col)} className="flex items-center gap-1 hover:text-foreground">
        {label}
        <ArrowUpDown className={`h-3 w-3 ${active ? "text-primary" : "text-muted-foreground/60"}`} />
        {active && <span className="text-[10px] text-muted-foreground">{order}</span>}
      </button>
    </TableHead>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <Select value={value || "__all"} onValueChange={(v) => onChange(v === "__all" ? "" : v)}>
      <SelectTrigger className="w-[180px]">
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__all">All {label}s</SelectItem>
        {options.map((o) => (
          <SelectItem key={o} value={o}>
            {o}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function SizeBadge({ size }: { size: string }) {
  const s = size.toLowerCase();
  const className = useMemo(() => {
    if (s === "large") return "bg-primary text-primary-foreground";
    if (s === "medium") return "bg-accent text-accent-foreground";
    return "bg-secondary text-secondary-foreground";
  }, [s]);
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${className}`}>{size}</span>;
}
