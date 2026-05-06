import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowRight, Telescope, Clock, FileDown, Eye, MessagesSquare, Check, Loader2, ExternalLink, CircleDot } from "lucide-react";
import { ReportPreviewPane } from "@/components/ReportPreviewPane";
import { agentPipeline, stageToAgentIndex, type ReportStyle, type Agent } from "@/lib/mock-data";
import { createRun, subscribeToProgress, getRunStatus, getReportMarkdown, getReportDownloadUrl, listRunDocuments, type DocumentItem, type ProgressEvent } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const reportStyles: ReportStyle[] = ["General", "Academic", "Business", "Medical", "Technical", "Policy"];
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

const examples = [
  "Post-Chinchilla scaling laws and the rise of MoE",
  "Cardiovascular outcomes of GLP-1 receptor agonists",
  "EU AI Act enforcement and SME exemptions",
  "Solid-state battery commercialization bottlenecks",
];

const NewResearch = () => {
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState<ReportStyle>("Technical");
  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();
  const { currentWorkspace } = useWorkspace();

  const handleStart = async () => {
    if (topic.trim().length < 8) return;
    setSubmitting(true);
    try {
      const run = await createRun(topic, style.toLowerCase(), currentWorkspace?.id);
      setRunId(run.id);
      setRunning(true);
    } catch (err: any) {
      toast({
        title: "Failed to start research",
        description: err.message || "Check that the backend is running.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (running && runId) {
    return <ActiveRunWorkspace topic={topic} style={style} runId={runId} />;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="px-4 lg:px-8 py-12 max-w-4xl mx-auto"
    >
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs text-muted-foreground mb-5">
          <Telescope className="h-3 w-3 text-gold" /> New research run
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight mb-3">
          What are we <span className="font-serif-italic text-gold">investigating</span>?
        </h1>
        <p className="text-muted-foreground">
          Describe a topic. The staged pipeline will plan, search, analyze, draft, refine, and resolve citations.
        </p>
      </div>

      <div className="glass-strong rounded-2xl p-6 md:p-8 mb-6">
        <textarea
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. Compare carbon-capture technologies for cement manufacturing, focusing on TRL, cost per ton, and policy support across the EU and US…"
          rows={4}
          className="w-full bg-transparent resize-none text-lg leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none font-display"
        />
        <div className="flex flex-wrap gap-2 mt-3">
          {examples.map(e => (
            <button
              key={e}
              onClick={() => setTopic(e)}
              className="text-xs px-2.5 py-1 rounded-md bg-muted/50 hover:bg-gold/10 hover:text-gold text-muted-foreground transition"
            >
              {e}
            </button>
          ))}
        </div>

        <div className="mt-8 pt-6 border-t border-border/60">
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-2 font-mono">Report style</div>
          <div className="flex flex-wrap gap-1.5">
            {reportStyles.map(t => (
              <button
                key={t}
                onClick={() => setStyle(t)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                  style === t ? "bg-gold/15 border-gold/50 text-gold" : "bg-muted/30 border-transparent text-foreground/70 hover:border-border"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end mt-8 pt-6 border-t border-border/60">
          <button
            onClick={handleStart}
            disabled={topic.trim().length < 8 || submitting}
            className="inline-flex items-center gap-2 h-11 px-6 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition disabled:opacity-40 disabled:shadow-none"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {submitting ? "Starting…" : "Start Research Run"} <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

function ActiveRunWorkspace({ topic, style, runId }: { topic: string; style: ReportStyle; runId: string }) {
  const [stage, setStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [stageMessage, setStageMessage] = useState("Starting pipeline…");
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const esRef = useRef<EventSource | null>(null);
  const navigate = useNavigate();
  const stages = ["Scout", "Analyst", "Author I", "Author II", "Validator"];

  // Timer
  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // SSE progress subscription
  useEffect(() => {
    const es = subscribeToProgress(
      runId,
      (event: ProgressEvent) => {
        const agentIdx = stageToAgentIndex[event.stage] ?? stage;
        const stageLabel = STAGE_LABELS[event.stage] || `Running ${event.stage}…`;

        if (event.stage === "done") {
          setCompleted(true);
          setStage(5);
          setStageMessage(stageLabel);
          // Fetch the report markdown
          getReportMarkdown(runId).then(r => setReportMarkdown(r.markdown)).catch(() => {});
        } else if (event.stage === "failed") {
          setFailed(true);
          setStageMessage(event.message || stageLabel);
        } else {
          if (agentIdx >= 0) setStage(agentIdx);
          setStageMessage(event.message || stageLabel);
        }
      },
      () => {
        // On SSE error, poll for status instead
        getRunStatus(runId).then(run => {
          if (run.status === "done") {
            setCompleted(true);
            setStage(5);
            getReportMarkdown(runId).then(r => setReportMarkdown(r.markdown)).catch(() => {});
          } else if (run.status === "failed") {
            setFailed(true);
            setStageMessage(run.error_message || "Pipeline failed");
          }
        }).catch(() => {});
      },
    );
    esRef.current = es;
    return () => es.close();
  }, [runId]);

  // Poll for documents during run
  useEffect(() => {
    const pollDocs = setInterval(() => {
      listRunDocuments(runId).then(setDocuments).catch(() => {});
    }, 5000);
    if (completed || failed) clearInterval(pollDocs);
    return () => clearInterval(pollDocs);
  }, [runId, completed, failed]);

  // If completed, final doc fetch
  useEffect(() => {
    if (completed) {
      listRunDocuments(runId).then(setDocuments).catch(() => {});
    }
  }, [completed, runId]);

  const visibleSections = stage <= 1 ? 0 : stage === 2 ? 1 : stage === 3 ? 3 : 4;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="px-4 lg:px-6 py-6 max-w-[1600px] mx-auto">
      {/* Compact run header */}
      <motion.div
        layout
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-xl px-5 py-4 mb-5 flex flex-col md:flex-row md:items-center gap-3 md:gap-6"
      >
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {!completed && !failed && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gold opacity-75" />}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${completed ? "bg-sage" : failed ? "bg-destructive" : "bg-gold"}`} />
          </span>
          <span className="text-xs uppercase tracking-wider text-gold font-mono">
            {completed ? "Completed" : failed ? "Failed" : "Running"}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{topic}</div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
            <span>{runId.slice(0, 8)}</span><span>·</span><span>{style}</span><span>·</span>
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {fmt(elapsed)}</span>
          </div>
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-12 gap-5">
        {/* LEFT: Agent Timeline */}
        <aside className="lg:col-span-3 space-y-3">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono px-1">Agent Timeline</div>
          {agentPipeline.map((a, i) => {
            const status: Agent["status"] =
              i < stage ? "completed" : i === stage && !completed ? "running" : completed ? "completed" : "pending";
            return (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={`glass rounded-xl p-4 transition ${status === "running" ? "border-gold/40" : ""}`}
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
                <div className="flex items-center gap-2 text-[10px]">
                  <span className={`px-1.5 py-0.5 rounded font-mono ${
                    status === "completed" ? "bg-sage/15 text-sage" :
                    status === "running" ? "bg-gold/15 text-gold" :
                    "bg-muted/40 text-muted-foreground"
                  }`}>
                    {status === "completed" ? "Completed" : status === "running" ? "Running" : "Pending"}
                  </span>
                </div>
                {status !== "pending" && (
                  <ul className="space-y-1 text-[11px] text-muted-foreground mt-2">
                    {a.logs.map((l, j) => (
                      <li key={j} className="flex items-start gap-1.5 leading-snug">
                        <span className="text-gold/60 mt-0.5">›</span><span>{l}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </motion.div>
            );
          })}
        </aside>

        {/* CENTER: Live Report Preview */}
        <main className="lg:col-span-6">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono px-1 mb-3">
            Live Report Preview
          </div>
          <AnimatePresence mode="wait">
            {stage <= 1 && !completed ? (
              <motion.div
                key="early"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="glass-strong rounded-2xl p-10 text-center"
              >
                <Loader2 className="h-6 w-6 text-gold animate-spin mx-auto mb-4" />
                <div className="font-display text-2xl font-semibold mb-2">{stageMessage}</div>
                <div className="text-sm text-muted-foreground mb-8">
                  The {stages[stage]} stage is preparing inputs for the next agent.
                </div>
                <div className="space-y-3 text-left max-w-md mx-auto">
                  {[0,1,2,3].map(i => (
                    <div key={i} className="space-y-2">
                      <div className="h-3 w-1/3 bg-muted/60 rounded animate-pulse" />
                      <div className="h-2 w-full bg-muted/40 rounded animate-pulse" />
                      <div className="h-2 w-10/12 bg-muted/40 rounded animate-pulse" />
                    </div>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div key="report" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <ReportPreviewPane
                  markdown={reportMarkdown || undefined}
                  title={topic}
                  visibleSections={completed ? undefined : visibleSections}
                  showSkeletons={!completed}
                  showFigure={stage >= 3}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* RIGHT: Run Summary + Sources + Actions */}
        <aside className="lg:col-span-3 space-y-4">
          {/* Summary */}
          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">Run Summary</div>
            <dl className="space-y-2 text-xs">
              <Row k="Run ID" v={runId.slice(0, 8)} mono />
              <Row k="Status" v={completed ? "Completed" : failed ? "Failed" : "Running"} />
              <Row k="Style" v={style} />
              <Row k="Started" v="just now" />
              <Row k="Elapsed" v={fmt(elapsed)} mono />
              <Row k="Sources" v={String(documents.length)} mono />
              <Row k="Stage" v={completed ? "Done" : failed ? "Failed" : stages[Math.min(stage, 4)]} />
            </dl>
          </div>

          {/* Live source stream */}
          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3 flex items-center justify-between">
              <span>Live Source Stream</span>
              <span className="text-gold">{documents.length}</span>
            </div>
            <div className="space-y-2.5">
              <AnimatePresence>
                {documents.slice(0, 8).map((s, i) => {
                  const domain = (() => { try { return new URL(s.url).hostname; } catch { return s.url; } })();
                  return (
                    <motion.div
                      key={s.id}
                      initial={{ opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-start gap-2"
                    >
                      <CircleDot className="h-3 w-3 mt-0.5 shrink-0 text-gold" />
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-mono text-muted-foreground truncate">{domain}</div>
                        <div className="text-[12px] leading-snug line-clamp-2">{s.title || s.url}</div>
                        {s.relevance_score != null && (
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-0.5">
                            <span>{Math.round(s.relevance_score * 100)} rel.</span>
                          </div>
                        )}
                      </div>
                      <a href={s.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-gold mt-0.5">
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              {documents.length === 0 && (
                <div className="text-[11px] text-muted-foreground italic">Waiting for Scout to begin…</div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="glass rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">Actions</div>
            <div className="space-y-2">
              <ActionBtn
                disabled={!completed}
                icon={<Eye className="h-3.5 w-3.5" />}
                label="View Report"
                primary
                onClick={() => navigate(`/report?run=${runId}`)}
              />
              <ActionBtn
                disabled={!completed}
                icon={<FileDown className="h-3.5 w-3.5" />}
                label="Download PDF"
                onClick={() => { window.open(getReportDownloadUrl(runId), "_blank"); }}
              />
              <ActionBtn
                disabled={!completed}
                icon={<MessagesSquare className="h-3.5 w-3.5" />}
                label="Open RAG Chat"
                onClick={() => navigate(`/chats/${runId}`)}
              />
            </div>
            {!completed && !failed && (
              <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed">
                RAG chat becomes available after the report is generated.
              </p>
            )}
          </div>
        </aside>
      </div>
    </motion.div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className={mono ? "font-mono" : ""}>{v}</dd>
    </div>
  );
}

function ActionBtn({ disabled, icon, label, primary, onClick }: { disabled?: boolean; icon: React.ReactNode; label: string; primary?: boolean; onClick?: () => void }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`w-full inline-flex items-center justify-center gap-2 h-9 px-3 rounded-lg text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${
        primary ? "bg-gradient-gold text-gold-foreground shadow-glow disabled:shadow-none" : "glass hover:border-gold/50"
      }`}
    >
      {icon} {label}
    </button>
  );
}

function fmt(s: number) {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}m ${r.toString().padStart(2, "0")}s`;
}

export default NewResearch;
