import { Outlet } from "react-router-dom";
import { useState } from "react";
import { SidebarNavigation } from "./SidebarNavigation";
import { TopBar } from "./TopBar";
import { AmbientBackdrop } from "./AmbientBackdrop";

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="flex min-h-screen w-full">
      <AmbientBackdrop variant="subtle" />
      <SidebarNavigation collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} />
      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
