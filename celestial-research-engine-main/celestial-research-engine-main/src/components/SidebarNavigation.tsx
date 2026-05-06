import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FlaskConical,
  FileText,
  Database,
  BarChart3,
  MessagesSquare,
  Settings,
  Plus,
  ChevronDown,
  CircleDot,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
} from "lucide-react";
import { LynxWordmark, LynxMark } from "./Brand";
import { ThemeToggle } from "./ThemeToggle";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listRuns } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/runs", label: "Research Runs", icon: FlaskConical },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/sources", label: "Sources", icon: Database },
  { to: "/visualizations", label: "Visualizations", icon: BarChart3 },
  { to: "/chats", label: "RAG Chats", icon: MessagesSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

export function SidebarNavigation({ collapsed, onToggle }: Props) {
  const { pathname } = useLocation();
  const [wsOpen, setWsOpen] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [showNewWs, setShowNewWs] = useState(false);
  const { displayName, userInitials, signOut } = useAuth();
  const { workspaces, currentWorkspace, switchWorkspace, createWorkspace } = useWorkspace();

  const handleCreateWorkspace = async () => {
    if (!newWsName.trim()) return;
    try {
      await createWorkspace(newWsName.trim());
      setNewWsName("");
      setShowNewWs(false);
      setWsOpen(false);
    } catch {
      // ignore
    }
  };

  return (
    <aside
      className={`hidden lg:flex flex-col h-screen sticky top-0 border-r border-sidebar-border bg-sidebar/80 backdrop-blur-xl transition-[width] duration-300 ${
        collapsed ? "w-[68px]" : "w-[260px]"
      }`}
    >
      {/* Workspace switcher */}
      <div className="px-3 pt-4 pb-3 border-b border-sidebar-border/60">
        <div className="flex items-center justify-between">
          {collapsed ? (
            <NavLink to="/dashboard" className="mx-auto"><LynxMark size={26} /></NavLink>
          ) : (
            <button
              onClick={() => setWsOpen(v => !v)}
              className="flex items-center gap-2 flex-1 px-2 py-1.5 rounded-lg hover:bg-sidebar-accent/50 transition"
            >
              <LynxMark size={24} />
              <div className="flex-1 text-left min-w-0">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">Workspace</div>
                <div className="text-sm font-medium text-sidebar-foreground truncate">
                  {currentWorkspace?.name || "Select workspace"}
                </div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
          <button
            onClick={onToggle}
            className="ml-1 h-7 w-7 rounded-md hover:bg-sidebar-accent/60 flex items-center justify-center text-muted-foreground hover:text-foreground"
            aria-label="Collapse sidebar"
          >
            {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* New Research CTA */}
      <div className="p-3">
        <NavLink
          to="/new"
          className="group flex items-center gap-2 w-full bg-gradient-gold text-gold-foreground rounded-lg px-3 py-2.5 shadow-glow hover:shadow-elegant transition-all"
        >
          <Plus className="h-4 w-4 shrink-0" />
          {!collapsed && <span className="text-sm font-medium">New Research</span>}
        </NavLink>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        <div className="space-y-0.5">
          {nav.map(item => {
            const active = pathname === item.to || (item.to === "/runs" && pathname.startsWith("/runs"));
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`group flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                }`}
              >
                <item.icon className={`h-4 w-4 shrink-0 ${active ? "text-gold" : ""}`} />
                {!collapsed && <span className="truncate">{item.label}</span>}
                {!collapsed && active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gold" />}
              </NavLink>
            );
          })}
        </div>

        {/* Recent runs */}
        {!collapsed && (
          <RecentRunsSidebar />
        )}
      </nav>

      {/* Profile + theme */}
      <div className="border-t border-sidebar-border/60 p-3">
        <div className={`flex items-center ${collapsed ? "flex-col gap-2" : "gap-2"}`}>
          <div className="h-8 w-8 rounded-full bg-gradient-gold flex items-center justify-center text-gold-foreground text-xs font-semibold shrink-0">
            {userInitials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-sidebar-foreground truncate">{displayName}</div>
              <button
                onClick={signOut}
                className="text-[10px] text-muted-foreground hover:text-gold flex items-center gap-1 transition"
              >
                <LogOut className="h-2.5 w-2.5" /> Sign out
              </button>
            </div>
          )}
          <ThemeToggle />
        </div>
      </div>

      <AnimatePresence>
        {wsOpen && !collapsed && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute top-16 left-3 right-3 z-50 glass-strong rounded-xl p-2"
          >
            {workspaces.map(w => (
              <button
                key={w.id}
                onClick={() => { switchWorkspace(w.id); setWsOpen(false); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-accent/40 ${
                  currentWorkspace?.id === w.id ? "bg-gold/10 text-gold" : ""
                }`}
              >
                {w.name}
              </button>
            ))}
            <div className="my-1 h-px bg-border/60" />
            {showNewWs ? (
              <div className="px-3 py-2 flex items-center gap-2">
                <input
                  autoFocus
                  value={newWsName}
                  onChange={e => setNewWsName(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") handleCreateWorkspace(); if (e.key === "Escape") { setShowNewWs(false); setNewWsName(""); } }}
                  placeholder="Workspace name..."
                  className="flex-1 text-sm bg-transparent focus:outline-none placeholder:text-muted-foreground/50"
                />
                <button
                  onClick={handleCreateWorkspace}
                  className="text-xs text-gold hover:underline"
                >
                  Create
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowNewWs(true)}
                className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-accent/40 flex items-center gap-2 text-gold"
              >
                <Plus className="h-3.5 w-3.5" /> New Workspace
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  );
}

function RecentRunsSidebar() {
  const { currentWorkspace } = useWorkspace();
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(5, 0, currentWorkspace?.id),
    refetchInterval: 15000,
  });

  if (runs.length === 0) return null;

  return (
    <div className="mt-6 px-1">
      <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground/80 px-2 mb-2">Recent Runs</div>
      <div className="space-y-0.5">
        {runs.slice(0, 5).map(r => (
          <NavLink
            key={r.id}
            to={`/runs/${r.id}`}
            className="group flex items-start gap-2 px-2 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/40"
          >
            <CircleDot
              className={`h-3 w-3 mt-0.5 shrink-0 ${
                r.status === "running" || r.status === "pending" ? "text-gold animate-pulse" : r.status === "done" ? "text-sage" : "text-destructive"
              }`}
            />
            <span className="line-clamp-2 leading-snug">{r.topic}</span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
