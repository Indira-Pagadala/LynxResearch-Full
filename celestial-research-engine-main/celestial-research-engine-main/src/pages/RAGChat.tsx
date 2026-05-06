import { useParams, useNavigate, Link } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listChatThreads, getChatHistory, chatWithReport, listRuns } from "@/lib/api";
import { Send, Sparkles, MessagesSquare, ArrowLeft, Clock, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const RAGChats = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { currentWorkspace } = useWorkspace();

  // Thread list: show runs that have chat history + completed runs available for chat
  const { data: threads = [], isLoading: threadsLoading } = useQuery({
    queryKey: ["chat-threads"],
    queryFn: listChatThreads,
  });

  const { data: runs = [] } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(50, 0, currentWorkspace?.id),
  });

  const completedRuns = runs.filter(r => r.status === "done");

  if (!id) {
    return (
      <div className="px-4 lg:px-8 py-8 max-w-[1100px] mx-auto">
        <div className="mb-8">
          <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">RAG Chats</h1>
          <p className="text-muted-foreground">Conversations grounded in your generated reports.</p>
        </div>

        {threadsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 text-gold animate-spin" />
          </div>
        ) : (
          <>
            {/* Existing chat threads */}
            {threads.length > 0 && (
              <div className="glass rounded-2xl divide-y divide-border/60 mb-6">
                {threads.map(c => (
                  <button
                    key={c.run_id}
                    onClick={() => nav(`/chats/${c.run_id}`)}
                    className="w-full text-left flex items-start gap-4 px-5 py-4 hover:bg-muted/30 transition group"
                  >
                    <div className="h-9 w-9 rounded-lg bg-gold/10 text-gold flex items-center justify-center shrink-0">
                      <MessagesSquare className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate group-hover:text-gold transition">{c.topic}</div>
                      <div className="text-xs text-muted-foreground mt-1 truncate">{c.last_message}</div>
                      <div className="flex items-center gap-3 mt-2 text-[11px] text-muted-foreground font-mono">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {formatDistanceToNow(new Date(c.updated_at), { addSuffix: true })}
                        </span>
                        <span>·</span>
                        <span>{c.message_count} messages</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Available reports to start new chat */}
            {completedRuns.length > 0 && (
              <>
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">
                  {threads.length > 0 ? "Start a new chat" : "Available reports"}
                </div>
                <div className="glass rounded-2xl divide-y divide-border/60">
                  {completedRuns
                    .filter(r => !threads.some(t => t.run_id === r.id))
                    .map(r => (
                      <button
                        key={r.id}
                        onClick={() => nav(`/chats/${r.id}`)}
                        className="w-full text-left flex items-start gap-4 px-5 py-4 hover:bg-muted/30 transition group"
                      >
                        <div className="h-9 w-9 rounded-lg bg-muted/40 text-muted-foreground flex items-center justify-center shrink-0 group-hover:bg-gold/10 group-hover:text-gold transition">
                          <MessagesSquare className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate group-hover:text-gold transition">{r.topic}</div>
                          <div className="text-xs text-muted-foreground mt-1">Click to start a new RAG conversation</div>
                        </div>
                      </button>
                    ))}
                </div>
              </>
            )}

            {completedRuns.length === 0 && threads.length === 0 && (
              <div className="glass rounded-2xl p-12 text-center text-sm text-muted-foreground">
                No completed reports yet. Complete a research run to start chatting with your reports.
              </div>
            )}
          </>
        )}

        <div className="mt-6 text-xs text-muted-foreground text-center">
          To start a new RAG chat, open a completed report or click on one above.
        </div>
      </div>
    );
  }

  // Detail view — id is the run_id
  return <RagChatThread runId={id} />;
};

interface Msg { role: "user" | "assistant"; content: string }

function RagChatThread({ runId }: { runId: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Fetch the run info for the title
  const { data: runs = [] } = useQuery({
    queryKey: ["runs"],
    queryFn: () => listRuns(50),
  });
  const run = runs.find(r => r.id === runId);
  const chatTitle = run?.topic || "Research Report";

  // Load existing chat history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["chat-history", runId],
    queryFn: () => getChatHistory(runId),
  });

  useEffect(() => {
    if (history) {
      setMessages(history.map(m => ({ role: m.role, content: m.content })));
    }
  }, [history]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || sending) return;
    const question = input.trim();
    setInput("");

    // Optimistically add user message
    const updatedMessages = [...messages, { role: "user" as const, content: question }];
    setMessages(updatedMessages);

    setSending(true);
    try {
      const conversationHistory = updatedMessages.slice(-10).map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await chatWithReport(runId, question, conversationHistory);
      setMessages(prev => [...prev, { role: "assistant", content: response.answer }]);

      // Invalidate thread list cache so it updates
      queryClient.invalidateQueries({ queryKey: ["chat-threads"] });
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Error: ${err.message || "Failed to get response. Please try again."}`,
      }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] max-w-4xl mx-auto px-4 lg:px-6">
      <div className="py-5 border-b border-border/60">
        <Link to="/chats" className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-2">
          <ArrowLeft className="h-3 w-3" /> All chats
        </Link>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <span className="font-mono">{runId.slice(0, 8)}</span><span>·</span><span>RAG Chat</span>
        </div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">{chatTitle}</h1>
      </div>

      <div className="flex-1 overflow-y-auto py-6 space-y-5 scrollbar-thin">
        {historyLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 text-gold animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground">
            Ask anything about the research report. Your conversation will be saved.
          </div>
        ) : (
          messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "assistant" ? (
                <div className="max-w-[85%] space-y-3">
                  <div className="glass rounded-2xl rounded-tl-sm px-5 py-4 text-[15px] leading-relaxed">
                    {m.content.split(/(\[\d+\])/g).map((c, k) =>
                      /^\[\d+\]$/.test(c) ? (
                        <sup key={k} className="text-gold font-mono text-[11px] ml-0.5">{c}</sup>
                      ) : (<span key={k}>{c}</span>)
                    )}
                  </div>
                </div>
              ) : (
                <div className="max-w-[80%] rounded-2xl rounded-tr-sm px-5 py-3 bg-muted/60 text-[15px]">{m.content}</div>
              )}
            </motion.div>
          ))
        )}
        {sending && (
          <div className="flex justify-start">
            <div className="glass rounded-2xl rounded-tl-sm px-5 py-4">
              <Loader2 className="h-4 w-4 text-gold animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="py-4 border-t border-border/60">
        <div className="glass-strong rounded-2xl p-2 flex items-end gap-2">
          <Sparkles className="h-4 w-4 text-gold ml-3 mb-2.5" />
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask anything about the report…"
            rows={1}
            className="flex-1 bg-transparent resize-none py-2.5 px-1 focus:outline-none text-sm placeholder:text-muted-foreground/60"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="h-9 w-9 rounded-lg bg-gradient-gold text-gold-foreground flex items-center justify-center shadow-glow shrink-0 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default RAGChats;
