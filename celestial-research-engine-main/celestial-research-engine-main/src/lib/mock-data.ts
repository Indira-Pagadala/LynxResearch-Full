// src/lib/mock-data.ts
// Types only — all mock data arrays have been removed.
// Data now comes from the backend via src/lib/api.ts

export type AgentStatus = "completed" | "running" | "pending" | "queued" | "failed";

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  progress: number;
  logs: string[];
}

export interface Source {
  id: string;
  title: string;
  domain: string;
  url: string;
  summary: string;
  relevance: number;
  type: "Journal" | "News" | "Report" | "Preprint" | "Book" | "Dataset";
  date: string;
  reportId?: string;
  reportTitle?: string;
  status?: "collected" | "selected" | "cited" | "discarded";
}

export type ReportStyle = "General" | "Academic" | "Business" | "Medical" | "Technical" | "Policy";

export interface ResearchRun {
  id: string;
  topic: string;
  reportType: ReportStyle;
  status: "running" | "completed" | "failed" | "queued";
  startedAt: string;
  duration: string;
  sources: number;
  citations: number;
}

export interface RagChatThread {
  id: string;
  reportId: string;
  reportTitle: string;
  lastMessage: string;
  updatedAt: string;
  messages: number;
}

export interface VisualOutput {
  id: string;
  name: string;
  reportTitle: string;
  reportId: string;
  bars: number[];
}

// Static agent pipeline definition (maps to backend stages)
export const agentPipeline: Agent[] = [
  {
    id: "scout",
    name: "Scout",
    role: "Source Collection",
    status: "pending",
    progress: 0,
    logs: [
      "Planning search queries",
      "Collecting sources",
      "Filtering duplicates",
    ],
  },
  {
    id: "analyst",
    name: "Analyst",
    role: "Insight Extraction & Visual Outputs",
    status: "pending",
    progress: 0,
    logs: [
      "Extracting key findings",
      "Identifying statistics and tables",
      "Preparing visual evidence",
    ],
  },
  {
    id: "author1",
    name: "Author I",
    role: "Draft Generation",
    status: "pending",
    progress: 0,
    logs: [
      "Drafting core sections",
      "Building report structure",
    ],
  },
  {
    id: "author2",
    name: "Author II",
    role: "Refinement & Structuring",
    status: "pending",
    progress: 0,
    logs: ["Refining structure and clarity"],
  },
  {
    id: "validator",
    name: "Validator",
    role: "Citation Resolution & Finalization",
    status: "pending",
    progress: 0,
    logs: ["Resolving citations"],
  },
];

// Map backend stage names to agent index
export const stageToAgentIndex: Record<string, number> = {
  "scout": 0,
  "analyst": 1,
  "authoring": 2,
  "author1": 2,
  "author_1": 2,
  "author2": 3,
  "author_2": 3,
  "refinement": 3,
  "validator": 4,
  "validation": 4,
  "embedding": 4,
  "building_pdf": 4,
  "done": 5,
  "failed": -1,
};
