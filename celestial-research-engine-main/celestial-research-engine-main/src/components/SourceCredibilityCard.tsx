import { ExternalLink, ShieldCheck } from "lucide-react";
import type { Source } from "@/lib/mock-data";
import { motion } from "framer-motion";

export function SourceCredibilityCard({ source, index = 0 }: { source: Source; index?: number }) {
  const credColor =
    source.relevance >= 95 ? "text-gold" : source.relevance >= 88 ? "text-sage" : "text-accent-foreground";
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className="group glass rounded-xl p-4 hover:border-gold/40 hover:shadow-soft transition-all"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-6 w-6 rounded-md bg-muted flex items-center justify-center text-[9px] font-mono uppercase text-muted-foreground shrink-0">
            {source.domain.split(".")[0].slice(0, 2)}
          </div>
          <span className="text-xs text-muted-foreground truncate font-mono">{source.domain}</span>
        </div>
        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-muted/60 text-muted-foreground shrink-0">
          {source.type}
        </span>
      </div>
      <h4 className="text-sm font-medium leading-snug mb-2 line-clamp-2 group-hover:text-gold transition-colors">
        {source.title}
      </h4>
      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3 mb-3">{source.summary}</p>
      <div className="flex items-center justify-between pt-3 border-t border-border/60">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className={`h-3.5 w-3.5 ${credColor}`} />
          <span className={`text-xs font-mono font-medium ${credColor}`}>{source.relevance}</span>
          <span className="text-[10px] text-muted-foreground">relevance</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground">{source.date}</span>
          <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-gold" />
        </div>
      </div>
    </motion.article>
  );
}
