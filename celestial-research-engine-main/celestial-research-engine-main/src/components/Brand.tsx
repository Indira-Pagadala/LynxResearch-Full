import { motion } from "framer-motion";

export function LynxMark({ size = 28, animated = false }: { size?: number; animated?: boolean }) {
  const Wrap: any = animated ? motion.svg : "svg";
  const props = animated
    ? { initial: { rotate: -10, opacity: 0 }, animate: { rotate: 0, opacity: 1 }, transition: { duration: 0.8 } }
    : {};
  return (
    <Wrap
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <defs>
        <linearGradient id="lynx-g" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="hsl(var(--gold))" />
          <stop offset="100%" stopColor="hsl(var(--accent))" />
        </linearGradient>
      </defs>
      {/* outer ring */}
      <circle cx="20" cy="20" r="17" stroke="url(#lynx-g)" strokeWidth="1.2" opacity="0.5" />
      {/* inner constellation L */}
      <circle cx="13" cy="11" r="1.6" fill="hsl(var(--gold))" />
      <circle cx="13" cy="22" r="1.6" fill="hsl(var(--gold))" />
      <circle cx="13" cy="29" r="1.6" fill="hsl(var(--gold))" />
      <circle cx="22" cy="29" r="1.6" fill="hsl(var(--gold))" />
      <circle cx="28" cy="14" r="1.6" fill="hsl(var(--accent))" />
      <line x1="13" y1="11" x2="13" y2="29" stroke="hsl(var(--gold))" strokeWidth="0.8" opacity="0.6" />
      <line x1="13" y1="29" x2="22" y2="29" stroke="hsl(var(--gold))" strokeWidth="0.8" opacity="0.6" />
      <line x1="13" y1="22" x2="28" y2="14" stroke="hsl(var(--accent))" strokeWidth="0.6" opacity="0.5" strokeDasharray="1.5 1.5" />
    </Wrap>
  );
}

export function LynxWordmark({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <LynxMark size={26} />
      <div className="flex items-baseline gap-0.5">
        <span className="font-display text-xl font-semibold tracking-tight text-foreground">Lynx</span>
        <span className="font-display text-xl font-light italic text-gold">Research</span>
      </div>
    </div>
  );
}
