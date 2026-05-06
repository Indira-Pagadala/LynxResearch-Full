// src/lib/WorkspaceProvider.tsx
// Workspace context — manages workspace CRUD via backend API

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useAuth } from "./AuthProvider";

const API_BASE = "http://localhost:8000";

export interface Workspace {
  id: string;
  name: string;
  user_id: string;
  created_at: string;
}

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  loading: boolean;
  createWorkspace: (name: string) => Promise<Workspace>;
  switchWorkspace: (id: string) => void;
  deleteWorkspace: (id: string) => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

const CURRENT_WS_KEY = "lynx_current_workspace";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  const userId = user?.id || "anonymous";

  const fetchWorkspaces = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/?user_id=${userId}`);
      if (!res.ok) return;
      const data: Workspace[] = await res.json();
      setWorkspaces(data);

      // Restore last selected workspace
      const savedId = localStorage.getItem(CURRENT_WS_KEY);
      const match = data.find(w => w.id === savedId);
      if (match) {
        setCurrentWorkspace(match);
      } else if (data.length > 0) {
        setCurrentWorkspace(data[0]);
        localStorage.setItem(CURRENT_WS_KEY, data[0].id);
      } else {
        // Auto-create a default workspace
        const defaultWs = await createWorkspaceInternal("My Research");
        if (defaultWs) {
          setWorkspaces([defaultWs]);
          setCurrentWorkspace(defaultWs);
          localStorage.setItem(CURRENT_WS_KEY, defaultWs.id);
        }
      }
    } catch {
      // Backend may not be running yet — that's OK
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const createWorkspaceInternal = async (name: string): Promise<Workspace | null> => {
    try {
      const res = await fetch(`${API_BASE}/workspaces/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, user_id: userId }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  };

  useEffect(() => {
    if (userId) fetchWorkspaces();
  }, [userId, fetchWorkspaces]);

  const createWorkspace = async (name: string): Promise<Workspace> => {
    const ws = await createWorkspaceInternal(name);
    if (!ws) throw new Error("Failed to create workspace");
    setWorkspaces(prev => [...prev, ws]);
    setCurrentWorkspace(ws);
    localStorage.setItem(CURRENT_WS_KEY, ws.id);
    return ws;
  };

  const switchWorkspace = (id: string) => {
    const ws = workspaces.find(w => w.id === id);
    if (ws) {
      setCurrentWorkspace(ws);
      localStorage.setItem(CURRENT_WS_KEY, ws.id);
    }
  };

  const deleteWorkspace = async (id: string) => {
    await fetch(`${API_BASE}/workspaces/${id}`, { method: "DELETE" });
    setWorkspaces(prev => prev.filter(w => w.id !== id));
    if (currentWorkspace?.id === id) {
      const remaining = workspaces.filter(w => w.id !== id);
      if (remaining.length > 0) {
        setCurrentWorkspace(remaining[0]);
        localStorage.setItem(CURRENT_WS_KEY, remaining[0].id);
      } else {
        setCurrentWorkspace(null);
        localStorage.removeItem(CURRENT_WS_KEY);
      }
    }
  };

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        currentWorkspace,
        loading,
        createWorkspace,
        switchWorkspace,
        deleteWorkspace,
        refreshWorkspaces: fetchWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return ctx;
}
