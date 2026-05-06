import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme-provider";
import { motion, AnimatePresence } from "framer-motion";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className={`relative h-9 w-9 rounded-lg glass hover:border-gold/50 transition-colors flex items-center justify-center group ${className}`}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={theme}
          initial={{ opacity: 0, rotate: -90, scale: 0.6 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 90, scale: 0.6 }}
          transition={{ duration: 0.25 }}
          className="absolute inset-0 flex items-center justify-center text-foreground/80 group-hover:text-gold"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}
