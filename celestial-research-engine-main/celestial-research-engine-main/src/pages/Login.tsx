import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Mail, Lock, Loader2 } from "lucide-react";
import { LynxMark, LynxWordmark } from "@/components/Brand";
import { AmbientBackdrop } from "@/components/AmbientBackdrop";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/lib/AuthProvider";
import { useToast } from "@/hooks/use-toast";

const Login = () => {
  const nav = useNavigate();
  const { signInWithPassword, signInWithGoogle } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await signInWithPassword(email, password);
    setLoading(false);
    if (error) {
      toast({ title: "Sign in failed", description: error.message, variant: "destructive" });
    } else {
      nav("/dashboard");
    }
  };

  const handleGoogle = async () => {
    const { error } = await signInWithGoogle();
    if (error) {
      toast({ title: "Google sign in failed", description: error.message, variant: "destructive" });
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 py-10">
      <AmbientBackdrop variant="subtle" />
      <div className="absolute top-5 left-5"><Link to="/"><LynxWordmark /></Link></div>
      <div className="absolute top-5 right-5"><ThemeToggle /></div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-5xl glass-strong rounded-3xl overflow-hidden grid md:grid-cols-2 shadow-elegant"
      >
        {/* Brand panel */}
        <div className="relative hidden md:flex flex-col justify-between p-10 bg-gradient-to-br from-card to-muted/40 border-r border-border/60 overflow-hidden">
          <div className="absolute inset-0 -z-10 opacity-60">
            <div className="orb" style={{ background: "var(--gradient-orb-1)", width: 380, height: 380, top: -80, left: -80 }} />
            <div className="orb" style={{ background: "var(--gradient-orb-2)", width: 300, height: 300, bottom: -60, right: -60 }} />
          </div>
          <LynxMark size={36} />
          <div>
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-3">Welcome back</div>
            <h2 className="font-display text-4xl font-semibold tracking-tight leading-tight mb-4">
              Return to your <span className="font-serif-italic text-gold">research</span>.
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">
              Resume in-flight runs, open completed reports, and pick up RAG conversations where you left them.
            </p>
          </div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            A staged AI research pipeline.
          </div>
        </div>

        {/* Form */}
        <div className="p-8 md:p-10">
          <h1 className="font-display text-3xl font-semibold tracking-tight mb-2">Sign in</h1>
          <p className="text-sm text-muted-foreground mb-8">Use your email or continue with Google.</p>

          <button
            onClick={handleGoogle}
            className="w-full h-11 rounded-xl glass hover:border-gold/50 flex items-center justify-center gap-3 text-sm font-medium transition mb-5"
          >
            <GoogleIcon /> Continue with Google
          </button>

          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-border/60" />
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">or</span>
            <div className="flex-1 h-px bg-border/60" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <Field label="Email" icon={<Mail className="h-3.5 w-3.5" />}>
              <input
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@lab.org"
                className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/50"
              />
            </Field>
            <Field label="Password" icon={<Lock className="h-3.5 w-3.5" />}>
              <input
                type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/50"
              />
            </Field>
            <div className="flex justify-end">
              <a href="#" className="text-xs text-muted-foreground hover:text-gold">Forgot password?</a>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition inline-flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Sign in <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <p className="text-xs text-muted-foreground text-center mt-6">
            New to LynxResearch?{" "}
            <Link to="/signup" className="text-gold hover:underline">Create an account</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export function Field({ label, icon, children }: { label: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-mono">{label}</div>
      <div className="flex items-center gap-2 h-11 px-3 rounded-xl bg-muted/40 border border-border/60 focus-within:border-gold/60 transition">
        {icon && <span className="text-muted-foreground">{icon}</span>}
        {children}
      </div>
    </label>
  );
}

export function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.3-.4-3.5z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 44c5.3 0 10-2 13.6-5.3l-6.3-5.2C29.2 35.5 26.7 36.5 24 36.5c-5.2 0-9.6-3.3-11.2-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.3 5.7l6.3 5.2C41.5 35.6 44 30.2 44 24c0-1.3-.1-2.3-.4-3.5z"/>
    </svg>
  );
}

export default Login;
