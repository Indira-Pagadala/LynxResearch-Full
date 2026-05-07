import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Quote } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  /** Raw markdown from the backend — if provided, renders this instead of placeholder */
  markdown?: string;
  /** Report title override */
  title?: string;
  /** if set, controls how many sections are shown (progressive reveal during run) */
  visibleSections?: number;
  showSkeletons?: boolean;
  showFigure?: boolean;
  enableImageZoom?: boolean;
}

// Extract title and abstract from markdown for the header
function extractMeta(md: string) {
  const lines = md.split("\n");
  let title = "";
  let abstractLines: string[] = [];
  let bodyStart = 0;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith("# ") && !title) {
      title = trimmed.replace(/^#\s+/, "");
      bodyStart = i + 1;
      continue;
    }
    if (/^#{2,3}\s+/.test(trimmed)) {
      bodyStart = i;
      break;
    }
    if (trimmed && title) {
      abstractLines.push(trimmed);
    }
  }

  const abstract = abstractLines.join(" ");
  const body = lines.slice(bodyStart).join("\n");
  return { title, abstract, body };
}

// Count sections for progressive reveal
function countSections(md: string) {
  return (md.match(/^#{2,3}\s+/gm) || []).length;
}

// Trim markdown to only show N sections
function trimToSections(md: string, n: number) {
  const lines = md.split("\n");
  let sectionCount = 0;
  let endLine = lines.length;

  for (let i = 0; i < lines.length; i++) {
    if (/^#{2,3}\s+/.test(lines[i].trim())) {
      sectionCount++;
      if (sectionCount > n) {
        endLine = i;
        break;
      }
    }
  }

  return lines.slice(0, endLine).join("\n");
}

function normalizeMarkdownTables(md: string) {
  const lines = md.split("\n");
  const normalized: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const isTableLike = (s: string) => (s.match(/\|/g) || []).length >= 2;

    if (!isTableLike(line.trim())) {
      normalized.push(line);
      i += 1;
      continue;
    }

    const block: string[] = [];
    let j = i;
    while (j < lines.length && lines[j].trim() && isTableLike(lines[j].trim())) {
      block.push(lines[j].trim());
      j += 1;
    }

    if (block.length < 2) {
      normalized.push(line);
      i += 1;
      continue;
    }

    const parseCells = (row: string) => row.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
    const firstRowCells = parseCells(block[0]);
    const colCount = Math.max(1, firstRowCells.length);
    const separatorRegex = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/;
    const hasSeparator = separatorRegex.test(block[1]);

    const normalizedBlock: string[] = [];
    normalizedBlock.push(`| ${firstRowCells.join(" | ")} |`);
    if (hasSeparator) {
      normalizedBlock.push(
        `| ${parseCells(block[1]).slice(0, colCount).map(c => (c.includes(":") ? c : "---")).join(" | ")} |`,
      );
    } else {
      normalizedBlock.push(`| ${Array(colCount).fill("---").join(" | ")} |`);
    }

    const bodyStart = hasSeparator ? 2 : 1;
    for (let k = bodyStart; k < block.length; k++) {
      const cells = parseCells(block[k]);
      while (cells.length < colCount) cells.push("");
      normalizedBlock.push(`| ${cells.slice(0, colCount).join(" | ")} |`);
    }

    normalized.push(...normalizedBlock);
    i = j;
  }

  return normalized.join("\n");
}

export function ReportPreviewPane({
  markdown,
  title: titleProp,
  visibleSections,
  showSkeletons = false,
  showFigure = true,
  enableImageZoom = true,
}: Props) {
  const parsed = markdown ? extractMeta(markdown) : null;
  const displayTitle = parsed?.title || titleProp || "Research Report";
  const displayAbstract = parsed?.abstract || "";
  const body = parsed?.body || "";
  const total = markdown ? countSections(markdown) : 0;
  const [vs, setVs] = useState(visibleSections ?? total);
  const [zoomImage, setZoomImage] = useState<string | null>(null);

  useEffect(() => {
    if (visibleSections !== undefined) setVs(visibleSections);
    else setVs(total);
  }, [visibleSections, total]);

  // If no markdown and no sections, show placeholder
  if (!markdown && total === 0) {
    return (
      <article className="glass-strong rounded-2xl p-8 md:p-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-gold mb-3 font-mono">
          {showSkeletons ? "Drafting…" : "Report"}
        </div>
        <h1 className="font-display text-3xl md:text-4xl font-semibold leading-tight tracking-tight mb-4">
          {displayTitle}
        </h1>
        <div className="space-y-4 pt-4">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-1/3 bg-muted/60 rounded animate-pulse" />
              <div className="h-3 w-full bg-muted/40 rounded animate-pulse" />
              <div className="h-3 w-11/12 bg-muted/40 rounded animate-pulse" />
              <div className="h-3 w-9/12 bg-muted/40 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </article>
    );
  }

  const visibleBody = vs < total ? trimToSections(body, vs) : body;
  const normalizedVisibleBody = normalizeMarkdownTables(visibleBody);

  return (
    <article className="glass-strong rounded-2xl p-8 md:p-10">
      <div className="text-[11px] uppercase tracking-[0.2em] text-gold mb-3 font-mono">
        {showSkeletons ? "Drafting…" : "Report"}
      </div>
      <h1 className="font-display text-3xl md:text-4xl font-semibold leading-tight tracking-tight mb-4">
        {displayTitle}
      </h1>
      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-6 pb-6 border-b border-border/60">
        <span>LynxResearch</span>
        <span>·</span>
        <span>{new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</span>
        {total > 0 && (
          <>
            <span>·</span>
            <span>{total} sections</span>
          </>
        )}
      </div>

      {displayAbstract && (
        <div className="relative pl-4 border-l-2 border-gold/40 mb-8">
          <Quote className="absolute -left-3 -top-1 h-4 w-4 text-gold bg-card p-0.5 rounded" />
          <p className="font-serif-italic text-base text-muted-foreground leading-relaxed">
            {displayAbstract}
          </p>
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="report-content"
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => {
              const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
              return <h1 id={id} className="font-display text-3xl font-semibold mb-4 mt-8 tracking-tight">{children}</h1>;
            },
            h2: ({ children }) => {
              const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
              return <h2 id={id} className="font-display text-2xl font-semibold mb-3 mt-8 tracking-tight scroll-mt-20">{children}</h2>;
            },
            h3: ({ children }) => {
              const id = String(children).toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
              return <h3 id={id} className="font-display text-xl font-semibold mb-2 mt-6 tracking-tight scroll-mt-20">{children}</h3>;
            },
            h4: ({ children }) => (
              <h4 className="font-display text-lg font-semibold mb-2 mt-4">{children}</h4>
            ),
            p: ({ children }) => (
              <p className="text-[15px] leading-[1.75] mb-4 text-foreground/90 text-left">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-foreground">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-foreground/80">{children}</em>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-outside pl-6 mb-4 space-y-1.5 text-[15px] leading-[1.75] text-foreground/90 text-left">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside pl-6 mb-4 space-y-1.5 text-[15px] leading-[1.75] text-foreground/90 text-left">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="pl-1">{children}</li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-gold/40 pl-4 my-4 text-muted-foreground italic">{children}</blockquote>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto mb-8 rounded-lg border border-border/60">
                <table className="w-full text-sm table-auto">{children}</table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-muted/40 border-b border-border/60">{children}</thead>
            ),
            tbody: ({ children }) => (
              <tbody className="divide-y divide-border/40">{children}</tbody>
            ),
            tr: ({ children }) => (
              <tr className="hover:bg-muted/20 transition">{children}</tr>
            ),
            th: ({ children }) => (
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">{children}</th>
            ),
            td: ({ children }) => (
              <td className="px-4 py-2.5 text-sm align-top whitespace-normal break-words">{children}</td>
            ),
            img: ({ src, alt }) => {
              if (!enableImageZoom) {
                return (
                  <img
                    src={src}
                    alt={alt || "Report visualization"}
                    className="w-full max-w-[720px] max-h-[380px] object-contain mx-auto rounded-lg border border-border/60 bg-white/90 my-4"
                  />
                );
              }
              return (
                <button
                  type="button"
                  className="block my-4 w-full"
                  onClick={() => src && setZoomImage(String(src))}
                >
                  <img
                    src={src}
                    alt={alt || "Report visualization"}
                    className="w-full max-w-[720px] max-h-[380px] object-contain mx-auto rounded-lg border border-border/60 cursor-zoom-in bg-white/90"
                  />
                </button>
              );
            },
            code: ({ className, children, ...props }) => {
              const isInline = !className;
              if (isInline) {
                return (
                  <code className="px-1.5 py-0.5 rounded bg-muted/60 text-sm font-mono text-gold" {...props}>
                    {children}
                  </code>
                );
              }
              return (
                <pre className="mb-4 rounded-lg bg-muted/40 border border-border/60 p-4 overflow-x-auto">
                  <code className={`text-sm font-mono ${className || ""}`} {...props}>
                    {children}
                  </code>
                </pre>
              );
            },
            pre: ({ children }) => <>{children}</>,
            a: ({ href, children }) => {
              const isInternalRef = !!href && href.startsWith("#ref-");
              if (isInternalRef) {
                return (
                  <a
                    href={href}
                    className="text-gold hover:underline"
                    onClick={(e) => {
                      e.preventDefault();
                      const num = Number((href || "").replace("#ref-", ""));
                      const lists = document.querySelectorAll(".report-content ol");
                      const lastList = lists[lists.length - 1];
                      if (!lastList || !num) return;
                      const item = lastList.querySelector(`li:nth-child(${num})`) as HTMLElement | null;
                      item?.scrollIntoView({ behavior: "smooth", block: "center" });
                    }}
                  >
                    {children}
                  </a>
                );
              }
              return (
                <a href={href} target="_blank" rel="noreferrer" className="text-gold hover:underline">
                  {children}
                </a>
              );
            },
            hr: () => <hr className="my-6 border-border/60" />,
          }}
        >
          {normalizedVisibleBody}
        </ReactMarkdown>
      </motion.div>
      {enableImageZoom && zoomImage && (
        <div
          className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-6"
          onClick={() => setZoomImage(null)}
        >
          <img
            src={zoomImage}
            alt="Expanded visualization"
            className="max-w-[84vw] max-h-[78vh] rounded-lg shadow-2xl object-contain"
          />
        </div>
      )}

      {showSkeletons && vs < total && (
        <div className="space-y-4 pt-2">
          {[0, 1, 2].map(i => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-1/3 bg-muted/60 rounded animate-pulse" />
              <div className="h-3 w-full bg-muted/40 rounded animate-pulse" />
              <div className="h-3 w-11/12 bg-muted/40 rounded animate-pulse" />
              <div className="h-3 w-9/12 bg-muted/40 rounded animate-pulse" />
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
