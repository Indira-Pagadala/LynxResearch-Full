import { motion } from "framer-motion";

/** Decorative ambient layer: orbs + drifting stars + faint grain. */
export function AmbientBackdrop({ variant = "default" }: { variant?: "default" | "dense" | "subtle" }) {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* gradient base already on body */}
      <div className="absolute inset-0 star-bg opacity-40 dark:opacity-100" />
      <motion.div
        className="orb"
        style={{ background: "var(--gradient-orb-1)", width: 600, height: 600, top: -150, left: -100 }}
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="orb"
        style={{ background: "var(--gradient-orb-2)", width: 500, height: 500, bottom: -120, right: -80 }}
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      {variant === "dense" && (
        <motion.div
          className="orb"
          style={{ background: "var(--gradient-orb-1)", width: 380, height: 380, top: "40%", left: "50%" }}
          animate={{ x: [-50, 50, -50], y: [0, -30, 0] }}
          transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
    </div>
  );
}
