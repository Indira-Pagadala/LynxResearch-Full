import { useState } from "react";
import { useTheme } from "@/lib/theme-provider";
import { Pencil, Sun, Moon } from "lucide-react";
import type { ReportStyle } from "@/lib/mock-data";
import { useAuth } from "@/lib/AuthProvider";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { useQuery } from "@tanstack/react-query";
import { listRuns } from "@/lib/api";

const reportStyles: ReportStyle[] = ["General", "Academic", "Business", "Medical", "Technical", "Policy"];

const Settings = () => {
  const { theme, setTheme } = useTheme();
  const { displayName, userInitials, userEmail } = useAuth();
  const { currentWorkspace, workspaces } = useWorkspace();
  const [defaultStyle, setDefaultStyle] = useState<ReportStyle>("Academic");

  // Get run count for usage display
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", currentWorkspace?.id],
    queryFn: () => listRuns(100, 0, currentWorkspace?.id),
  });

  const used = runs.length;
  const limit = 50;

  return (
    <div className="px-4 lg:px-8 py-8 max-w-3xl mx-auto">
      <h1 className="font-display text-4xl font-semibold tracking-tight mb-2">Settings</h1>
      <p className="text-muted-foreground mb-8">Account, workspace, defaults, and appearance.</p>

      {/* Account */}
      <section className="glass rounded-2xl p-6 mb-4">
        <div className="flex items-start justify-between mb-5">
          <h2 className="font-display text-xl font-semibold">Account</h2>
          <button className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg glass hover:border-gold/50 text-xs">
            <Pencil className="h-3 w-3" /> Edit
          </button>
        </div>
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-full bg-gradient-gold flex items-center justify-center text-gold-foreground font-semibold">{userInitials}</div>
          <div className="flex-1">
            <div className="text-sm font-medium">{displayName}</div>
            <div className="text-xs text-muted-foreground">{userEmail || "No email"}</div>
          </div>
        </div>
      </section>

      {/* Workspace */}
      <section className="glass rounded-2xl p-6 mb-4">
        <h2 className="font-display text-xl font-semibold mb-5">Workspace</h2>
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <Row k="Workspace" v={currentWorkspace?.name || "None"} />
          <Row k="Total Workspaces" v={String(workspaces.length)} />
          <Row k="Runs in workspace" v={String(used)} />
          <Row k="Run limit" v={`${limit} / month`} />
        </div>
        <div className="mt-5">
          <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
            <span>Runs used this month</span>
            <span className="font-mono">{used} / {limit}</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div className="h-full bg-gradient-gold" style={{ width: `${Math.min((used/limit)*100, 100)}%` }} />
          </div>
        </div>
      </section>

      {/* Defaults */}
      <section className="glass rounded-2xl p-6 mb-4">
        <h2 className="font-display text-xl font-semibold mb-5">Research Defaults</h2>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-mono">Default report style</div>
          <div className="flex flex-wrap gap-1.5">
            {reportStyles.map(s => (
              <button
                key={s}
                onClick={() => setDefaultStyle(s)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition ${
                  defaultStyle === s ? "bg-gold/15 border-gold/50 text-gold" : "bg-muted/30 border-transparent hover:border-border"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Appearance */}
      <section className="glass rounded-2xl p-6">
        <h2 className="font-display text-xl font-semibold mb-1">Appearance</h2>
        <p className="text-sm text-muted-foreground mb-5">Switch between Celestial Inkwell and Botanical Parchment.</p>
        <div className="flex gap-2">
          <button
            onClick={() => setTheme("dark")}
            className={`inline-flex items-center gap-2 h-10 px-4 rounded-lg border transition ${theme === "dark" ? "bg-gold/15 border-gold/50 text-gold" : "glass hover:border-gold/40"}`}
          >
            <Moon className="h-3.5 w-3.5" /> Dark
          </button>
          <button
            onClick={() => setTheme("light")}
            className={`inline-flex items-center gap-2 h-10 px-4 rounded-lg border transition ${theme === "light" ? "bg-gold/15 border-gold/50 text-gold" : "glass hover:border-gold/40"}`}
          >
            <Sun className="h-3.5 w-3.5" /> Light
          </button>
        </div>
      </section>
    </div>
  );
};

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-1">{k}</div>
      <div>{v}</div>
    </div>
  );
}

export default Settings;
