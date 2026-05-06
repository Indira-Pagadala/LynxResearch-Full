import { useParams, Link, useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  Check, Loader2, FileDown, MessagesSquare, ArrowLeft, Clock, ChevronRight, Eye, ExternalLink, CircleDot,
} from "lucide-react";
import { agentPipeline, stageToAgentIndex, type Agent } from "@/lib/mock-data";
import { ReportPreviewPane } from "@/components/ReportPreviewPane";
import { useQuery } from "@tanstack/react-query";
import {
  getRunStatus, subscribeToProgress, getReportMarkdown, getReportDownloadUrl,
  listRunDocuments, type ProgressEvent, type DocumentItem,
} from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
const STAGE_LABELS: Record<string, string> = {
  scout: "Scouting sources",
  analyst: "Collecting data",
  authoring: "Generating sections",
  authoring_2: "Generating sections",
  validating: "Finalizing report",
  embedding: "Finalizing report",
  building_pdf: "Finalizing report",
  done: "Run complete",
  failed: "Run failed",
};

const RunDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const runId = id ?? "";

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRunStatus(runId),
    enabled: !!runId,
    refetchInterval: 5000,
  });

  const [stage, setStage] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [stageMessage, setStageMessage] = useState("");
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const esRef = useRef<EventSource | null>(null);

  // Sync from poll data
  useEffect(() => {
    if (!run) return;
    if (run.status === "done") {
      setCompleted(true);
      setStage(5);
      getReportMarkdown(runId).then(r => setReportMarkdown(r.markdown)).catch(() => {});
    } else if (run.status === "failed") {
      setFailed(true);
      setStageMessage(run.error_message || "Pipeline failed");
    } else {
      const idx = stageToAgentIndex[run.current_stage || ""] ?? 0;
      if (idx >= 0) setStage(idx);
      setStageMessage(STAGE_LABELS[run.current_stage || ""] || (run.current_stage || ""));
    }
  }, [run]);

  // SSE for running runs
  useEffect(() => {
    if (!runId || completed || failed) return;
    if (run && run.status !== "running" && run.status !== "pending") return;

    const es = subscribeToProgress(
      runId,
      (event: ProgressEvent) => {
        const agentIdx = stageToAgentIndex[event.stage] ?? stage;
        const stageLabel = STAGE_LABELS[event.stage] || `Running ${event.stage}…`;
        if (event.stage === "done") {
          setCompleted(true);
          setStage(5);
          setStageMessage(stageLabel);
          getReportMarkdown(runId).then(r => setReportMarkdown(r.markdown)).catch(() => {});
        } else if (event.stage === "failed") {
          setFailed(true);
          setStageMessage(event.message || stageLabel);
        } else {
          if (agentIdx >= 0) setStage(agentIdx);
          setStageMessage(event.message || stageLabel);
        }
      },
    );
    esRef.current = es;
    return () => es.close();
  }, [runId, run?.status]);

  // Fetch documents
  useEffect(() => {
    if (!runId) return;
    listRunDocuments(runId).then(setDocuments).catch(() => {});
    if (completed || failed) return;
    const t = setInterval(() => {
      listRunDocuments(runId).then(setDocuments).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, [runId, completed, failed]);

  if (runLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 text-gold animate-spin" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="px-4 lg:px-6 py-12 text-center text-muted-foreground">
        Run not found.
      </div>
    );
  }

  const isRunning = run.status === "running" || run.status === "pending";
  const isDone = run.status === "done" || completed;
  const stages = ["Scout", "Analyst", "Author I", "Author II", "Validator"];
  const visibleSections = stage <= 1 ? 0 : stage === 2 ? 1 : stage === 3 ? 3 : 4;

  return (
    <div className="px-4 lg:px-6 py-6 max-w-[1600px] mx-auto">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-5">
        <Link to="/runs" className="hover:text-foreground flex items-center gap-1">
          <ArrowLeft className="h-3 w-3" /> Runs
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="font-mono text-foreground">{runId.slice(0, 8)}</span>
      </div>

      <div className="glass rounded-xl px-5 py-4 mb-5 flex flex-col md:flex-row md:items-center gap-3 md:gap-6">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {isRunning && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gold opacity-75" />}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${isDone ? "bg-sage" : failed ? "bg-destructive" : "bg-gold"}`} />
          </span>
          <span className="text-xs uppercase tracking-wider text-gold font-mono">
            {isDone ? "Completed" : failed ? "Failed" : "Running"}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{run.topic}</div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
            <span>{runId.slice(0, 8)}</span><span>·</span><span>{capitalize(run.status === "done" ? "completed" : run.status)}</span><span>·</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" /> {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-12 gap-5">
        {/* LEFT: agent timeline */}
        <aside className="lg:col-span-3 space-y-3">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono px-1">Agent Timeline</div>
          {agentPipeline.map((a, i) => {
            const status: Agent["status"] =
              i < stage ? "completed" : i === stage && !isDone ? "running" : isDone ? "completed" : "pending";
            return (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={`glass rounded-xl p-4 ${status === "running" ? "border-gold/40" : ""}`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{a.name}</div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{a.role}</div>
                  </div>
                  {status === "completed" ? <Check className="h-4 w-4 text-gold" /> :
                    status === "running" ? <Loader2 className="h-4 w-4 text-gold animate-spin" /> :
                    <CircleDot className="h-3 w-3 text-muted-foreground/40" />}
                </div>
                <ul className="space-y-1 text-[11px] text-muted-foreground">
                  {a.logs.map((l, j) => (
                    <li key={j} className="flex items-start gap-1.5 leading-snug">
                      <span className="text-gold/60 mt-0.5">›</span><span>{l}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </aside>

        {/* CENTER */}
        <main className="lg:col-span-6">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono px-1 mb-3">
            {isDone ? "Report Preview" : "Live Report Preview"}
          </div>
          <ReportPreviewPane
            markdown={reportMarkdown || undefined}
            title={run.topic}
            visibleSections={isDone ? undefined : visibleSections}
            showSkeletons={!isDone}
            showFigure={stage >= 3 || isDone}
          />
        </main>

        {/* RIGHT */}
        <aside className="lg:col-span-3 space-y-4">
          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">Run Summary</div>
            <dl className="space-y-2 text-xs">
              <Row k="Run ID" v={runId.slice(0, 8)} mono />
              <Row k="Status" v={isDone ? "Completed" : failed ? "Failed" : capitalize(run.status)} />
              <Row k="Progress" v={`${run.progress}%`} mono />
              <Row k="Started" v={formatDistanceToNow(new Date(run.created_at), { addSuffix: true })} />
              <Row k="Sources" v={String(documents.length)} mono />
              <Row k="Stage" v={isDone ? "Run complete" : (stageMessage || STAGE_LABELS[run.current_stage || ""] || (run.current_stage || "—"))} />
            </dl>
          </div>

          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3 flex items-center justify-between">
              <span>Source Stream</span>
              <span className="text-gold">{documents.length}</span>
            </div>
            <div className="space-y-2.5">
              {documents.slice(0, 8).map(s => {
                const domain = (() => { try { return new URL(s.url).hostname; } catch { return s.url; } })();
                return (
                  <div key={s.id} className="flex items-start gap-2">
                    <CircleDot className="h-3 w-3 mt-0.5 shrink-0 text-gold" />
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] font-mono text-muted-foreground truncate">{domain}</div>
                      <div className="text-[12px] leading-snug line-clamp-2">{s.title || s.url}</div>
                    </div>
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-gold mt-0.5">
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                );
              })}
              {documents.length === 0 && (
                <div className="text-[11px] text-muted-foreground italic">
                  {isRunning ? "Waiting for sources…" : "No sources collected"}
                </div>
              )}
            </div>
          </div>

          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">Actions</div>
            <div className="space-y-2">
              <button
                disabled={!isDone}
                onClick={() => navigate(`/report?run=${runId}`)}
                className="w-full inline-flex items-center justify-center gap-2 h-9 rounded-lg bg-gradient-gold text-gold-foreground text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-glow disabled:shadow-none"
              >
                <Eye className="h-3.5 w-3.5" /> View Report
              </button>
              <button
                disabled={!isDone}
                onClick={() => window.open(getReportDownloadUrl(runId), "_blank")}
                className="w-full inline-flex items-center justify-center gap-2 h-9 rounded-lg glass text-xs disabled:opacity-40 disabled:cursor-not-allowed hover:border-gold/50 transition"
              >
                <FileDown className="h-3.5 w-3.5" /> Download PDF
              </button>
              <button
                disabled={!isDone}
                onClick={() => navigate(`/chats/${runId}`)}
                className="w-full inline-flex items-center justify-center gap-2 h-9 rounded-lg glass text-xs disabled:opacity-40 disabled:cursor-not-allowed hover:border-gold/50 transition"
              >
                <MessagesSquare className="h-3.5 w-3.5" /> Open RAG Chat
              </button>
            </div>
            {!isDone && !failed && (
              <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed">
                RAG chat becomes available after the report is generated.
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className={mono ? "font-mono" : ""}>{v}</dd>
    </div>
  );
}

export default RunDetail;
