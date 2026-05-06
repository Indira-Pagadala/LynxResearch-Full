import { motion } from "framer-motion";
import { Telescope, Microscope, PenLine, Sparkles, BookMarked, Check, Loader2 } from "lucide-react";

const pipelineNodes = [
  { id: "scout", name: "Scout", role: "Source Collection", icon: Telescope },
  { id: "analyst", name: "Analyst", role: "Insight Extraction & Visual Outputs", icon: Microscope },
  { id: "author1", name: "Author I", role: "Draft Generation", icon: PenLine },
  { id: "author2", name: "Author II", role: "Refinement & Structuring", icon: Sparkles },
  { id: "validator", name: "Validator", role: "Citation Resolution & Finalization", icon: BookMarked },
];

interface Props {
  activeIndex?: number;
  compact?: boolean;
}

export function AgentPipeline3D({ activeIndex = 2, compact = false }: Props) {
  return (
    <div className="relative w-full">
      <div className="absolute top-8 left-[8%] right-[8%] h-px bg-gradient-to-r from-transparent via-border to-transparent hidden md:block" />
      <motion.div
        className="absolute top-8 left-[8%] h-px bg-gradient-to-r from-gold via-gold to-transparent hidden md:block"
        initial={{ width: 0 }}
        animate={{ width: `${(activeIndex / (pipelineNodes.length - 1)) * 84}%` }}
        transition={{ duration: 1.4, ease: "easeOut" }}
      />

      <div className={`relative grid grid-cols-2 md:grid-cols-5 gap-4 ${compact ? "" : "md:gap-2"}`}>
        {pipelineNodes.map((n, i) => {
          const status = i < activeIndex ? "completed" : i === activeIndex ? "running" : "pending";
          const Icon = n.icon;
          return (
            <motion.div
              key={n.id}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="flex flex-col items-center text-center"
            >
              <div
                className={`relative h-16 w-16 rounded-2xl flex items-center justify-center glass-strong ${
                  status === "running" ? "border-gold/60" : ""
                } ${status === "completed" ? "border-gold/40" : ""}`}
                style={{
                  background:
                    status === "completed"
                      ? "linear-gradient(135deg, hsl(var(--card)), hsl(var(--gold) / 0.12))"
                      : status === "running"
                      ? "linear-gradient(135deg, hsl(var(--card)), hsl(var(--gold) / 0.2))"
                      : undefined,
                }}
              >
                <Icon className={`h-6 w-6 ${status === "pending" ? "text-muted-foreground/50" : "text-gold"}`} />
                <div className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full glass flex items-center justify-center">
                  {status === "completed" ? (
                    <Check className="h-3 w-3 text-gold" />
                  ) : status === "running" ? (
                    <Loader2 className="h-3 w-3 text-gold animate-spin" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                  )}
                </div>
              </div>
              <div className="mt-3">
                <div className="font-display text-base font-semibold tracking-tight">{n.name}</div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5 leading-tight px-1">{n.role}</div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
