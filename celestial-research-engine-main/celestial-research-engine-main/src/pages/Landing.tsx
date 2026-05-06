import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Network,
  MessagesSquare,
  Quote,
} from "lucide-react";
import { LynxWordmark, LynxMark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AmbientBackdrop } from "@/components/AmbientBackdrop";
import { AgentPipeline3D } from "@/components/AgentPipeline3D";
import { SourceCredibilityCard } from "@/components/SourceCredibilityCard";
// Static decorative data for the landing page showcase
const landingSources = [
  { id: "s1", title: "Transformer Scaling Laws Revisited", domain: "arxiv.org", relevance: 96 },
  { id: "s2", title: "Enterprise AI Adoption — 2026 Survey", domain: "stanford.edu", relevance: 92 },
  { id: "s3", title: "Mechanistic Interpretability of MoE", domain: "nature.com", relevance: 98 },
  { id: "s4", title: "Energy Footprint of Frontier Models", domain: "ieee.org", relevance: 90 },
];

function ParallaxSection({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.8, ease: [0.21, 0.47, 0.32, 0.98] }}
      className={`relative max-w-7xl mx-auto px-6 lg:px-10 py-28 ${className}`}
    >
      {children}
    </motion.section>
  );
}

function HeroFloatingMockup() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [40, -40]);
  const rotate = useTransform(scrollYProgress, [0, 1], [-2, 2]);

  const stages = ["Scout", "Analyst", "Author I", "Author II", "Validator"];

  return (
    <motion.div
      ref={ref}
      style={{ y, rotateX: rotate, transformPerspective: 1200 }}
      className="relative mx-auto max-w-5xl"
    >
      <div className="relative glass-strong rounded-2xl p-1.5 shadow-elegant">
        <div className="rounded-xl overflow-hidden bg-card/90">
          <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-border/60 bg-background/40">
            <div className="h-2.5 w-2.5 rounded-full bg-muted" />
            <div className="h-2.5 w-2.5 rounded-full bg-muted" />
            <div className="h-2.5 w-2.5 rounded-full bg-muted" />
            <div className="ml-3 text-[11px] font-mono text-muted-foreground">lynxresearch.app/runs/r-3401</div>
          </div>
          <div className="grid grid-cols-12 gap-0 min-h-[380px]">
            <div className="col-span-2 border-r border-border/60 p-3 space-y-1.5 bg-sidebar/40">
              {["Dashboard", "Runs", "Reports", "Sources", "Chats"].map((s, i) => (
                <div
                  key={s}
                  className={`text-[10px] px-2 py-1.5 rounded ${
                    i === 1 ? "bg-gold/10 text-gold" : "text-muted-foreground"
                  }`}
                >
                  {s}
                </div>
              ))}
            </div>
            <div className="col-span-3 border-r border-border/60 p-3 space-y-2">
              <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Pipeline</div>
              {stages.map((a, i) => (
                <div key={a} className="flex items-center gap-2">
                  <div
                    className={`h-1.5 w-1.5 rounded-full ${
                      i < 2 ? "bg-gold" : i === 2 ? "bg-gold animate-pulse" : "bg-muted"
                    }`}
                  />
                  <span className="text-[10px]">{a}</span>
                </div>
              ))}
            </div>
            <div className="col-span-5 p-4">
              <div className="text-[9px] text-gold uppercase tracking-wider font-mono mb-1">Drafting</div>
              <div className="font-display text-base font-semibold leading-tight mb-2">
                Frontier Model Scaling, Efficiency, and the Post-Chinchilla Regime
              </div>
              <div className="space-y-1.5">
                {[100, 96, 88, 92, 70].map((w, i) => (
                  <motion.div
                    key={i}
                    initial={{ width: 0 }}
                    animate={{ width: `${w}%` }}
                    transition={{ duration: 1.2, delay: i * 0.15 }}
                    className="h-1.5 bg-foreground/10 rounded"
                  />
                ))}
              </div>
              <div className="mt-4 h-16 flex items-end gap-1">
                {[40, 60, 75, 85, 92, 95, 88].map((h, i) => (
                  <div key={i} className="flex-1 bg-gradient-to-t from-gold/30 to-gold rounded-sm" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className="col-span-2 border-l border-border/60 p-3 space-y-2 bg-muted/20">
              <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Sources</div>
              {landingSources.slice(0, 3).map(s => (
                <div key={s.id} className="space-y-0.5">
                  <div className="text-[9px] font-mono text-muted-foreground">{s.domain}</div>
                  <div className="text-[10px] leading-tight line-clamp-2">{s.title}</div>
                  <div className="text-[9px] text-gold">{s.relevance} rel.</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -left-8 top-20 hidden md:block glass-strong rounded-xl p-3 w-44 shadow-elegant"
      >
        <div className="flex items-center gap-2 mb-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-gold" />
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Citation Resolved</span>
        </div>
        <div className="text-xs font-medium">Nature, 2026</div>
        <div className="text-[10px] text-muted-foreground">relevance 98 · cited</div>
      </motion.div>
      <motion.div
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="absolute -right-8 top-32 hidden md:block glass-strong rounded-xl p-3 w-48 shadow-elegant"
      >
        <div className="flex items-center gap-2 mb-1.5">
          <Network className="h-3.5 w-3.5 text-gold" />
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Visual outputs</span>
        </div>
        <div className="text-xs font-medium">Charts & tables ready</div>
        <div className="text-[10px] text-muted-foreground">Generated during analysis</div>
      </motion.div>
    </motion.div>
  );
}

const Landing = () => {
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <AmbientBackdrop variant="dense" />

      <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/60 border-b border-border/40">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <Link to="/"><LynxWordmark /></Link>
          <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
            <a href="#pipeline" className="hover:text-foreground transition">Pipeline</a>
            <a href="#sources" className="hover:text-foreground transition">Sources</a>
            <a href="#report" className="hover:text-foreground transition">Reports</a>
            <a href="#chat" className="hover:text-foreground transition">RAG</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              to="/login"
              className="hidden sm:inline-flex items-center gap-1.5 h-9 px-4 rounded-lg bg-gradient-gold text-gold-foreground text-sm font-medium hover:shadow-glow transition"
            >
              Open Workspace <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative pt-20 pb-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center max-w-4xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs text-muted-foreground mb-8">
              <Sparkles className="h-3 w-3 text-gold" />
              <span>A staged AI research pipeline</span>
              <span className="text-gold/60">· v2.4</span>
            </div>
            <h1 className="font-display text-6xl md:text-8xl font-semibold leading-[0.95] tracking-tight mb-6">
              The digital{" "}
              <span className="font-serif-italic text-gold">observatory</span>
              <br />
              for knowledge.
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed mb-10">
              From a single research topic to a structured, citation-backed report generated through a staged AI research pipeline.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/login"
                className="group inline-flex items-center gap-2 h-12 px-6 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition"
              >
                Start Research
                <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          </motion.div>

          <div className="mt-20">
            <HeroFloatingMockup />
          </div>
        </div>
      </section>

      {/* PIPELINE */}
      <ParallaxSection className="border-t border-border/40">
        <div id="pipeline" className="text-center max-w-3xl mx-auto mb-16">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-4">02 · The Pipeline</div>
          <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight mb-5">
            A staged <span className="font-serif-italic text-gold">research pipeline</span>.
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Each stage owns a discrete responsibility and hands off explicit, inspectable artifacts. Charts, tables, and forecasts are generated during analysis — not by a separate visualization system. Citation resolution is performed by the Validator at the end.
          </p>
        </div>
        <div className="glass-strong rounded-3xl p-10 md:p-14">
          <AgentPipeline3D activeIndex={5} />
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-10">
          {[
            { title: "Scout", body: "Plans queries, collects candidate sources, deduplicates and filters." },
            { title: "Analyst", body: "Extracts findings, statistics, and prepares charts, tables, and forecasts." },
            { title: "Author I & II", body: "Drafts core sections, then refines flow, structure, and clarity." },
            { title: "Validator", body: "Resolves inline references, structures citations, prepares the final export." },
          ].map(c => (
            <div key={c.title} className="glass rounded-xl p-5">
              <div className="text-[10px] uppercase tracking-wider text-gold font-mono mb-2">{c.title}</div>
              <div className="text-sm text-muted-foreground leading-relaxed">{c.body}</div>
            </div>
          ))}
        </div>
      </ParallaxSection>

      {/* SOURCES */}
      <ParallaxSection>
        <div id="sources" className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-4">03 · Source Intelligence</div>
            <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight mb-5">
              Every claim, <span className="font-serif-italic text-gold">traceable</span>.
            </h2>
            <p className="text-lg text-muted-foreground leading-relaxed mb-6">
              Sources are ranked, deduplicated, and resolved against report references. Each citation in the final report links back to the source it was drawn from.
            </p>
            <ul className="space-y-3">
              {[
                "Ranked by relevance score",
                "Deduplicated across queries",
                "Resolved against inline references",
              ].map(t => (
                <li key={t} className="flex items-start gap-3 text-sm">
                  <ShieldCheck className="h-4 w-4 text-gold mt-0.5 shrink-0" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            {landingSources.map((s, i) => (
              <SourceCredibilityCard key={s.id} source={s as any} index={i} />
            ))}
          </div>
        </div>
      </ParallaxSection>

      {/* REPORT */}
      <ParallaxSection>
        <div id="report" className="text-center max-w-3xl mx-auto mb-12">
          <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-4">04 · Citation-Backed</div>
          <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight mb-5">
            Reports written like a <span className="font-serif-italic text-gold">scholar</span>.
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Inline citations, embedded visual outputs, structured sections — drafted by the Author stages, finalized by the Validator.
          </p>
        </div>
        <div className="relative">
          <div className="absolute -inset-8 bg-gradient-orb-2 opacity-50 blur-3xl pointer-events-none" />
          <div className="relative">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="glass-strong rounded-2xl p-8 md:p-12 max-w-3xl mx-auto"
            >
              <div className="text-[10px] uppercase tracking-[0.2em] text-gold mb-3 font-mono">Live preview</div>
              <h3 className="font-display text-3xl font-semibold tracking-tight mb-4">
                Mechanistic Interpretability of Mixture-of-Experts Architectures
              </h3>
              <motion.p
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3, duration: 0.8 }}
                className="font-serif-italic text-muted-foreground leading-relaxed mb-6 border-l-2 border-gold/40 pl-4"
              >
                Across 200+ surveyed model variants, the data-to-parameter ratio that minimizes total cost of ownership is closer to 28:1 than the original 20:1 estimate
                <sup className="text-gold font-mono text-[11px] ml-0.5">[1]</sup>, driven by sustained reductions in high-quality token cost
                <sup className="text-gold font-mono text-[11px] ml-0.5">[2]</sup>.
              </motion.p>
              <motion.p
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.7, duration: 0.8 }}
                className="text-[15px] leading-[1.75] text-foreground/90"
              >
                Mixture-of-experts architectures now account for an estimated 71% of newly trained frontier-class models
                <sup className="text-gold font-mono text-[11px] ml-0.5">[3]</sup>. Mechanistic interpretability work has begun to identify stable specialization patterns within expert layers.
              </motion.p>
            </motion.div>
          </div>
        </div>
      </ParallaxSection>

      {/* RAG */}
      <ParallaxSection>
        <div id="chat" className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="order-2 lg:order-1 glass-strong rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5 pb-4 border-b border-border/60">
              <MessagesSquare className="h-4 w-4 text-gold" />
              <span className="text-sm font-medium">Conversation with report</span>
              <span className="ml-auto text-[10px] font-mono text-muted-foreground">r-3401</span>
            </div>
            <div className="space-y-4">
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-2.5 bg-muted/60 text-sm">
                  How did the data-to-parameter ratio shift from Chinchilla?
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[88%] space-y-2">
                  <div className="rounded-2xl rounded-tl-sm px-4 py-3 glass text-sm leading-relaxed">
                    The optimal ratio shifted from approximately 20:1 to 28:1
                    <sup className="text-gold font-mono text-[11px]">[1]</sup>, primarily driven by lower high-quality token cost and inference dominating lifetime compute
                    <sup className="text-gold font-mono text-[11px]">[2]</sup>.
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {landingSources.slice(0, 2).map(s => (
                      <div key={s.id} className="text-[10px] glass rounded-md px-2 py-1 flex items-center gap-1.5">
                        <span className="h-1 w-1 rounded-full bg-gold" />
                        <span className="font-mono text-muted-foreground">{s.domain}</span>
                        <span className="text-gold">{s.relevance}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="order-1 lg:order-2">
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-4">05 · RAG Conversation</div>
            <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight mb-5">
              Ask the <span className="font-serif-italic text-gold">report itself</span>.
            </h2>
            <p className="text-lg text-muted-foreground leading-relaxed">
              Once a report is generated, open a RAG chat to interrogate it. Every answer is grounded in retrieved passages and surfaced as inline citations.
            </p>
          </div>
        </div>
      </ParallaxSection>

      {/* FINAL CTA */}
      <ParallaxSection>
        <div className="relative glass-strong rounded-3xl px-8 md:px-16 py-20 md:py-28 text-center overflow-hidden">
          <div className="absolute inset-0 -z-10 opacity-50">
            <div className="orb" style={{ background: "var(--gradient-orb-1)", width: 500, height: 500, top: -100, left: "20%" }} />
            <div className="orb" style={{ background: "var(--gradient-orb-2)", width: 400, height: 400, bottom: -80, right: "15%" }} />
          </div>
          <Quote className="h-8 w-8 text-gold mx-auto mb-6 opacity-60" />
          <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight mb-5 max-w-3xl mx-auto leading-tight">
            One topic. <span className="font-serif-italic text-gold">One report.</span>
            <br />Hours, not weeks.
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10">
            Sign in and start your first staged research run.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/login"
              className="group inline-flex items-center gap-2 h-12 px-7 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition"
            >
              Start your first run <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition" />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 h-12 px-7 rounded-xl glass hover:border-gold/50 font-medium transition"
            >
              Open Workspace
            </Link>
          </div>
        </div>
      </ParallaxSection>

      <footer className="border-t border-border/40 py-10">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <LynxMark size={22} />
            <span className="text-xs text-muted-foreground">© 2026 LynxResearch · A digital observatory for knowledge.</span>
          </div>
          <div className="flex items-center gap-5 text-xs text-muted-foreground">
            <a href="#" className="hover:text-foreground">Docs</a>
            <a href="#" className="hover:text-foreground">Privacy</a>
            <a href="#" className="hover:text-foreground">Status</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
