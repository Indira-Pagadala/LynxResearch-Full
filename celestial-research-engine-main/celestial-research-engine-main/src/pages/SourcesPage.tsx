import { ExternalLink, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { listRuns, listRunDocuments, type DocumentItem } from "@/lib/api";
import { useState, useEffect } from "react";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const SourcesPage = () => {
  const { currentWorkspace } = useWorkspace();
  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(50, 0, currentWorkspace?.id),
  });

  const [allDocs, setAllDocs] = useState<(DocumentItem & { runTopic: string })[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);

  useEffect(() => {
    if (runs.length === 0) {
      setLoadingDocs(false);
      return;
    }

    const fetchAll = async () => {
      setLoadingDocs(true);
      const results: (DocumentItem & { runTopic: string })[] = [];
      for (const run of runs) {
        try {
          const docs = await listRunDocuments(run.id);
          for (const d of docs) {
            results.push({ ...d, runTopic: run.topic });
          }
        } catch {
          // skip failed fetches
        }
      }
      setAllDocs(results);
      setLoadingDocs(false);
    };

    fetchAll();
  }, [runs]);

  const isLoading = runsLoading || loadingDocs;

  return (
    <div className="px-4 lg:px-8 py-8 max-w-[1400px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">Sources</h1>
        <p className="text-muted-foreground">Every source used across generated reports.</p>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-5 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-mono border-b border-border/60">
          <div className="col-span-5">Title</div>
          <div className="col-span-2">Domain</div>
          <div className="col-span-4">Report</div>
          <div className="col-span-1 text-right">Open</div>
        </div>
        <div className="divide-y divide-border/60">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 text-gold animate-spin" />
            </div>
          ) : allDocs.length === 0 ? (
            <div className="text-center py-12 text-sm text-muted-foreground">
              No sources yet. Sources will appear here as research runs complete.
            </div>
          ) : (
            allDocs.map(s => {
              const domain = (() => { try { return new URL(s.url).hostname; } catch { return s.url; } })();
              return (
                <div key={s.id} className="grid grid-cols-12 gap-4 px-5 py-4 hover:bg-muted/30 transition items-center">
                  <div className="col-span-5 min-w-0">
                    <div className="text-sm font-medium truncate">{s.title || s.url}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">{s.source_type}</div>
                  </div>
                  <div className="col-span-2 text-xs text-muted-foreground font-mono truncate">{domain}</div>
                  <div className="col-span-4 text-xs text-muted-foreground truncate">{s.runTopic}</div>
                  <div className="col-span-1 flex justify-end">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="h-8 w-8 rounded-md hover:bg-gold/10 flex items-center justify-center text-muted-foreground hover:text-gold"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
export default SourcesPage;
