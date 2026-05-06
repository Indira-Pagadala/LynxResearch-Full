import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FileText, FlaskConical, Database, Quote, ArrowUpRight, ArrowRight, Plus, CircleDot, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listRuns, type RunListItem } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { useAuth } from "@/lib/AuthProvider";
import { useWorkspace } from "@/lib/WorkspaceProvider";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

const Dashboard = () => {
  const { displayName } = useAuth();
  const { currentWorkspace } = useWorkspace();

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(10, 0, currentWorkspace?.id),
    refetchInterval: 15000,
  });

  const completedRuns = runs.filter(r => r.status === "done");
  const activeRuns = runs.filter(r => r.status === "running" || r.status === "pending");

  const stats = [
    { label: "Total Reports", value: String(completedRuns.length), delta: "Completed runs", icon: FileText },
    { label: "Active Runs", value: String(activeRuns.length), delta: activeRuns.length > 0 ? "In progress" : "None running", icon: FlaskConical, accent: activeRuns.length > 0 },
    { label: "Total Runs", value: String(runs.length), delta: "All time", icon: Database },
    { label: "Pipeline", value: "5-agent", delta: "Scout → Validator", icon: Quote },
  ];

  return (
    <div className="px-4 lg:px-8 py-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-10">
        <div>
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-2">
            Workspace · {currentWorkspace?.name || "Research Lab"}
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight mb-2">
            {getGreeting()}, <span className="font-serif-italic text-gold">{displayName}</span>.
          </h1>
          <p className="text-muted-foreground">
            {activeRuns.length > 0
              ? `${activeRuns.length} run${activeRuns.length > 1 ? "s" : ""} in flight. ${completedRuns.length} reports generated.`
              : `${completedRuns.length} reports generated. Start a new research run to begin.`}
          </p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition self-start md:self-auto"
        >
          <Plus className="h-4 w-4" /> New Research
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className={`glass rounded-xl p-5 hover:border-gold/40 transition group ${s.accent ? "border-gold/30" : ""}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="h-9 w-9 rounded-lg bg-muted/60 flex items-center justify-center group-hover:bg-gold/10 transition">
                <s.icon className={`h-4 w-4 ${s.accent ? "text-gold" : "text-foreground/70"}`} />
              </div>
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-gold transition" />
            </div>
            <div className="font-display text-3xl font-semibold tracking-tight">{s.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
            <div className="text-[11px] text-gold/80 font-mono mt-2">{s.delta}</div>
          </motion.div>
        ))}
      </div>

      {/* Two-column */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent runs */}
        <div className="lg:col-span-2 glass rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border/60">
            <div>
              <h2 className="font-display text-xl font-semibold">Recent Runs</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Ordered by most recent</p>
            </div>
            <Link to="/runs" className="text-xs text-gold hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="divide-y divide-border/60">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 text-gold animate-spin" />
              </div>
            ) : runs.length === 0 ? (
              <div className="text-center py-12 text-sm text-muted-foreground">
                No research runs yet. Start your first one!
              </div>
            ) : (
              runs.slice(0, 5).map(r => (
                <Link
                  key={r.id}
                  to={`/runs/${r.id}`}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-muted/30 transition group"
                >
                  <CircleDot
                    className={`h-3.5 w-3.5 shrink-0 ${
                      r.status === "running" || r.status === "pending" ? "text-gold animate-pulse" : r.status === "done" ? "text-sage" : "text-destructive"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate group-hover:text-gold transition">{r.topic}</div>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
                      <span className="font-mono">{r.id.slice(0, 8)}</span>
                      <span>·</span>
                      <span>{capitalize(r.report_style)}</span>
                      <span>·</span>
                      <span>{formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}</span>
                    </div>
                  </div>
                  <div className="hidden md:flex items-center gap-5 text-[11px] text-muted-foreground font-mono">
                    <div className="text-center">
                      <div className="text-foreground text-sm">{r.progress}%</div>
                      <div>progress</div>
                    </div>
                    <div className="text-center">
                      <div className="text-foreground text-sm">{capitalize(r.status === "done" ? "completed" : r.status)}</div>
                      <div>status</div>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Activity */}
        <div className="glass rounded-2xl">
          <div className="px-5 py-4 border-b border-border/60">
            <h2 className="font-display text-xl font-semibold">Pipeline</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Agent execution stages</p>
          </div>
          <div className="p-5 space-y-4 relative">
            <div className="absolute left-[26px] top-7 bottom-7 w-px bg-border/60" />
            {["Scout — Source Collection", "Analyst — Insight Extraction", "Author I — Draft Generation", "Author II — Refinement", "Validator — Citation Resolution"].map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="relative flex gap-3"
              >
                <div className="h-3 w-3 rounded-full bg-gold/20 border border-gold/60 mt-1 z-10 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm leading-snug">{a}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground font-mono">
                      Stage {i + 1}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
