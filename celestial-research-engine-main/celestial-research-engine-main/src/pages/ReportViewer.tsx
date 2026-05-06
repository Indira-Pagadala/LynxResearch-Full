import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReportMarkdown, getReportDownloadUrl } from "@/lib/api";
import { ReportPreviewPane } from "@/components/ReportPreviewPane";
import { FileDown, Share2, Loader2, MessagesSquare } from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";

const ReportViewer = () => {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run") || "";
  const [activeSection, setActiveSection] = useState("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report-markdown", runId],
    queryFn: () => getReportMarkdown(runId),
    enabled: !!runId,
  });

  // Parse sections for TOC
  const sections = (report?.markdown || "")
    .split("\n")
    .filter(line => /^#{2,3}\s+/.test(line.trim()))
    .map(line => {
      const heading = line.trim().replace(/^#{2,3}\s+/, "");
      const level = line.trim().startsWith("### ") ? 3 : 2;
      const id = heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
      return { id, heading, level };
    });

  // IntersectionObserver for active section tracking
  useEffect(() => {
    if (!report?.markdown || sections.length === 0) return;

    // Small delay to let the DOM render headings
    const timer = setTimeout(() => {
      if (observerRef.current) observerRef.current.disconnect();

      const headingEls = sections
        .map(s => document.getElementById(s.id))
        .filter(Boolean) as HTMLElement[];

      if (headingEls.length === 0) return;

      observerRef.current = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              setActiveSection(entry.target.id);
              break;
            }
          }
        },
        { rootMargin: "-80px 0px -70% 0px", threshold: 0 }
      );

      headingEls.forEach(el => observerRef.current!.observe(el));
    }, 300);

    return () => {
      clearTimeout(timer);
      observerRef.current?.disconnect();
    };
  }, [report?.markdown, sections.length]);

  const scrollToSection = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveSection(id);
    }
  }, []);

  if (!runId) {
    return (
      <div className="px-4 lg:px-6 py-12 text-center text-muted-foreground">
        No run specified. Navigate here from a completed report.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 text-gold animate-spin" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="px-4 lg:px-6 py-12 text-center text-muted-foreground">
        Report not found. The run may still be in progress.
      </div>
    );
  }

  return (
    <div className="px-4 lg:px-6 py-8 max-w-[1500px] mx-auto">
      <div className="grid lg:grid-cols-12 gap-6">
        {/* TOC sidebar — clickable with active state */}
        <aside className="lg:col-span-2">
          <div className="sticky top-20">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono mb-3">Contents</div>
            <nav className="space-y-0.5 text-sm max-h-[calc(100vh-160px)] overflow-y-auto scrollbar-thin pr-1">
              {sections.map(s => (
                <button
                  key={s.id}
                  onClick={() => scrollToSection(s.id)}
                  className={`block w-full text-left px-3 py-1.5 rounded-md transition text-[13px] leading-snug ${
                    s.level === 3 ? "pl-6" : ""
                  } ${
                    activeSection === s.id
                      ? "bg-gold/10 text-gold border-l-2 border-gold"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                  }`}
                >
                  {s.heading}
                </button>
              ))}
            </nav>

            {/* Quick actions under TOC */}
            <div className="mt-6 pt-4 border-t border-border/40 space-y-2">
              <Link
                to={`/chats/${runId}`}
                className="flex items-center gap-2 text-xs text-muted-foreground hover:text-gold transition"
              >
                <MessagesSquare className="h-3.5 w-3.5" /> Ask this report
              </Link>
            </div>
          </div>
        </aside>

        {/* Report — expanded to full remaining width */}
        <main className="lg:col-span-10">
          <div className="flex items-center justify-end gap-2 mb-4">
            <button className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg glass text-xs hover:border-gold/50">
              <Share2 className="h-3 w-3" /> Share
            </button>
            <button
              onClick={() => window.open(getReportDownloadUrl(runId), "_blank")}
              className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg glass text-xs hover:border-gold/50"
            >
              <FileDown className="h-3 w-3" /> Export PDF
            </button>
          </div>
          <ReportPreviewPane markdown={report.markdown} />
        </main>
      </div>
    </div>
  );
};

export default ReportViewer;
