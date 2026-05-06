import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { listRuns, listRunCharts, type ChartItem } from "@/lib/api";
import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const API_BASE = "http://localhost:8000";

interface ChartWithMeta extends ChartItem {
  runTopic: string;
  runId: string;
}

const Visualizations = () => {
  const { currentWorkspace } = useWorkspace();
  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(50, 0, currentWorkspace?.id),
  });

  const [allCharts, setAllCharts] = useState<ChartWithMeta[]>([]);
  const [loadingCharts, setLoadingCharts] = useState(true);
  const [zoomChart, setZoomChart] = useState<ChartWithMeta | null>(null);

  useEffect(() => {
    if (runs.length === 0) {
      setLoadingCharts(false);
      return;
    }

    const fetchAll = async () => {
      setLoadingCharts(true);
      const results: ChartWithMeta[] = [];
      for (const run of runs) {
        try {
          const charts = await listRunCharts(run.id);
          for (const c of charts) {
            results.push({ ...c, runTopic: run.topic, runId: run.id });
          }
        } catch {
          // skip
        }
      }
      setAllCharts(results);
      setLoadingCharts(false);
    };

    fetchAll();
  }, [runs]);

  const isLoading = runsLoading || loadingCharts;

  return (
    <div className="px-4 lg:px-8 py-8 max-w-[1400px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">Visualizations</h1>
        <p className="text-muted-foreground">Visual outputs generated during analysis across reports.</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-5 w-5 text-gold animate-spin" />
        </div>
      ) : allCharts.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center text-sm text-muted-foreground">
          No visualizations yet. Charts will appear here as analysis stages complete.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {allCharts.map((v, i) => (
            <motion.div
              key={`${v.runId}-${v.filename}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="glass rounded-xl p-5"
            >
              <div className="font-display text-lg font-semibold mb-1 leading-tight">
                {v.filename.replace(/\.(png|jpg|jpeg|svg)$/i, "").replace(/[_-]/g, " ")}
              </div>
              <div className="text-xs text-muted-foreground mb-4 line-clamp-1">{v.runTopic}</div>
              <div className="rounded-lg overflow-hidden bg-white">
                <button type="button" className="w-full" onClick={() => setZoomChart(v)}>
                  <img
                    src={`${API_BASE}${v.url}`}
                    alt={v.filename}
                    className="w-full h-auto cursor-zoom-in"
                    loading="lazy"
                  />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
      {zoomChart && (
        <div
          className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-6"
          onClick={() => setZoomChart(null)}
        >
          <img
            src={`${API_BASE}${zoomChart.url}`}
            alt={zoomChart.filename}
            className="max-w-[95vw] max-h-[90vh] rounded-lg bg-white p-2"
          />
        </div>
      )}
    </div>
  );
};
export default Visualizations;
