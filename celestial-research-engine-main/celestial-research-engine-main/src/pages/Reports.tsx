import { Link } from "react-router-dom";
import { FileText, FileDown, Eye, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listRuns, getReportDownloadUrl } from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { formatISTTimestamp } from "@/lib/time";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const Reports = () => {
  const { currentWorkspace } = useWorkspace();
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(50, 0, currentWorkspace?.id),
  });

  const completed = runs.filter(r => r.status === "done");

  return (
    <div className="px-4 lg:px-8 py-8 max-w-[1400px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">Reports</h1>
        <p className="text-muted-foreground">Finalized, citation-resolved reports.</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-5 w-5 text-gold animate-spin" />
        </div>
      ) : completed.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center text-sm text-muted-foreground">
          No completed reports yet. Start a research run to generate your first report.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {completed.map(r => (
            <div key={r.id} className="glass rounded-2xl p-6 hover:border-gold/40 transition group">
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-3">
                <FileText className="h-3 w-3 text-gold" /> {capitalize(r.report_style)} · completed
              </div>
              <h2 className="font-display text-xl font-semibold leading-snug mb-3 group-hover:text-gold transition">{r.topic}</h2>
              <div className="flex items-center gap-4 text-xs text-muted-foreground mb-5">
                <span>{r.progress}% complete</span>
                <span>{formatISTTimestamp(r.created_at)}</span>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/report?run=${r.id}`}
                  className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-gradient-gold text-gold-foreground text-xs font-medium shadow-glow"
                >
                  <Eye className="h-3 w-3" /> View Report
                </Link>
                <button
                  onClick={() => window.open(getReportDownloadUrl(r.id), "_blank")}
                  className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg glass hover:border-gold/50 text-xs transition"
                >
                  <FileDown className="h-3 w-3" /> Download PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
export default Reports;
