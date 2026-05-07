import { Link } from "react-router-dom";
import { CircleDot, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listRuns } from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { formatISTTimestamp } from "@/lib/time";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const Runs = () => {
  const { currentWorkspace } = useWorkspace();
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(50, 0, currentWorkspace?.id),
    refetchInterval: 10000,
  });

  return (
    <div className="px-4 lg:px-8 py-8 max-w-[1400px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">Research Runs</h1>
        <p className="text-muted-foreground">Every investigation, with full pipeline execution provenance.</p>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-5 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-mono border-b border-border/60">
          <div className="col-span-6">Topic</div>
          <div className="col-span-2">Style</div>
          <div className="col-span-2 text-right">Progress</div>
          <div className="col-span-2 text-right">Started</div>
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
            runs.map(r => (
              <Link
                key={r.id}
                to={`/runs/${r.id}`}
                className="grid grid-cols-12 gap-4 px-5 py-4 hover:bg-muted/30 transition group items-center"
              >
                <div className="col-span-6 flex items-center gap-3 min-w-0">
                  <CircleDot className={`h-3.5 w-3.5 shrink-0 ${
                    r.status === "running" || r.status === "pending" ? "text-gold animate-pulse" : r.status === "done" ? "text-sage" : "text-destructive"
                  }`} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate group-hover:text-gold transition">{r.topic}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">
                      {r.id.slice(0, 8)} · {r.status === "done" ? "completed" : r.status}
                    </div>
                  </div>
                </div>
                <div className="col-span-2 text-xs text-muted-foreground">{capitalize(r.report_style)}</div>
                <div className="col-span-2 text-right text-sm font-mono">{r.progress}%</div>
                <div className="col-span-2 text-right text-xs text-muted-foreground">
                  {formatISTTimestamp(r.created_at)}
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Runs;
