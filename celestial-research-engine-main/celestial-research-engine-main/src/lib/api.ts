// src/lib/api.ts
// Thin API client for the LynxResearch backend

const API_BASE = "http://localhost:8000";

// ── Types matching backend schemas ──────────────────────────

export interface RunStatus {
  id: string;
  topic: string;
  status: string;
  progress: number;
  current_stage: string | null;
  error_message: string | null;
  workspace_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface RunListItem {
  id: string;
  topic: string;
  report_style: string;
  status: string;
  progress: number;
  current_stage: string | null;
  workspace_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ReportMetadata {
  id: string;
  run_id: string;
  word_count: number | null;
  page_count: number | null;
  pdf_path: string | null;
  created_at: string;
}

export interface ReportMarkdown {
  run_id: string;
  markdown: string;
}

export interface ChatMessage {
  id: string;
  run_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatThread {
  run_id: string;
  topic: string;
  last_message: string;
  message_count: number;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  run_id: string;
  url: string;
  title: string | null;
  source_type: string;
  relevance_score: number | null;
  created_at: string;
}

export interface ChartItem {
  filename: string;
  url: string;
}

export interface ProgressEvent {
  run_id: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
  type?: string; // "heartbeat" for keep-alive
}

// ── API Functions ───────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ── Runs ────────────────────────────────────────────────────

export async function createRun(topic: string, reportStyle: string, workspaceId?: string): Promise<RunStatus> {
  return apiFetch<RunStatus>("/runs/", {
    method: "POST",
    body: JSON.stringify({ topic, report_style: reportStyle, workspace_id: workspaceId || null }),
  });
}

export async function listRuns(limit = 20, offset = 0, workspaceId?: string): Promise<RunListItem[]> {
  let url = `/runs/?limit=${limit}&offset=${offset}`;
  if (workspaceId) url += `&workspace_id=${workspaceId}`;
  return apiFetch<RunListItem[]>(url);
}

export async function getRunStatus(runId: string): Promise<RunStatus> {
  return apiFetch<RunStatus>(`/runs/${runId}`);
}

export function subscribeToProgress(
  runId: string,
  onEvent: (event: ProgressEvent) => void,
  onError?: (error: Event) => void,
): EventSource {
  const es = new EventSource(`${API_BASE}/runs/${runId}/progress`);
  es.onmessage = (e) => {
    try {
      const data: ProgressEvent = JSON.parse(e.data);
      if (data.type === "heartbeat") return;
      onEvent(data);
      if (data.stage === "done" || data.stage === "failed") {
        es.close();
      }
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = (e) => {
    onError?.(e);
    es.close();
  };
  return es;
}

// ── Documents (Sources) ─────────────────────────────────────

export async function listRunDocuments(runId: string): Promise<DocumentItem[]> {
  return apiFetch<DocumentItem[]>(`/runs/${runId}/documents`);
}

// ── Charts ──────────────────────────────────────────────────

export async function listRunCharts(runId: string): Promise<ChartItem[]> {
  return apiFetch<ChartItem[]>(`/runs/${runId}/charts`);
}

export function getChartImageUrl(runId: string, filename: string): string {
  return `${API_BASE}/runs/${runId}/charts/${filename}`;
}

// ── Reports ─────────────────────────────────────────────────

export async function getReportMetadata(runId: string): Promise<ReportMetadata> {
  return apiFetch<ReportMetadata>(`/reports/${runId}`);
}

export async function getReportMarkdown(runId: string): Promise<ReportMarkdown> {
  return apiFetch<ReportMarkdown>(`/reports/${runId}/markdown`);
}

export function getReportDownloadUrl(runId: string): string {
  return `${API_BASE}/reports/${runId}/download`;
}

// ── Chat ────────────────────────────────────────────────────

export async function listChatThreads(): Promise<ChatThread[]> {
  return apiFetch<ChatThread[]>("/chat/threads");
}

export async function getChatHistory(runId: string): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(`/chat/${runId}/history`);
}

export async function chatWithReport(
  runId: string,
  question: string,
  conversationHistory: { role: string; content: string }[] = [],
): Promise<{ answer: string; run_id: string }> {
  return apiFetch<{ answer: string; run_id: string }>(`/chat/${runId}`, {
    method: "POST",
    body: JSON.stringify({
      question,
      conversation_history: conversationHistory,
    }),
  });
}
