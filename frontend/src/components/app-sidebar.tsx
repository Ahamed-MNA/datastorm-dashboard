import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Store, Map as MapIcon, Wallet, Sparkles, Activity, BarChart3 } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const items = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Outlets", url: "/outlets", icon: Store },
  { title: "Map", url: "/map", icon: MapIcon },
  { title: "Budget", url: "/budget", icon: Wallet },
  { title: "Campaign Monitoring", url: "/monitoring", icon: Activity },
  { title: "Pilot Evaluation", url: "/evaluation", icon: BarChart3 },
] as const;

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const isActive = (url: string) =>
    url === "/" ? pathname === "/" : pathname === url || pathname.startsWith(url + "/");

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border/40">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="font-serif text-base leading-tight text-sidebar-foreground">
              Outlet Intelligence
            </span>
            <span className="text-[10px] uppercase tracking-wider text-sidebar-foreground/60">
              Data Mavericks · v2
            </span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)} tooltip={item.title}>
                    <Link to={item.url} className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border/40">
        <div className="px-2 py-2 text-[10px] leading-relaxed text-sidebar-foreground/60 group-data-[collapsible=icon]:hidden">
          DataStorm v7.0 · Beverage Distributor Track
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
