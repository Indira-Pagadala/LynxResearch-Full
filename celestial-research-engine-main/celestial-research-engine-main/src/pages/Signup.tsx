import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Mail, Lock, User, Loader2 } from "lucide-react";
import { LynxMark, LynxWordmark } from "@/components/Brand";
import { AmbientBackdrop } from "@/components/AmbientBackdrop";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Field, GoogleIcon } from "./Login";
import { useAuth } from "@/lib/AuthProvider";
import { useToast } from "@/hooks/use-toast";

const Signup = () => {
  const nav = useNavigate();
  const { signUp, signInWithGoogle } = useAuth();
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await signUp(email, password, name);
    setLoading(false);
    if (error) {
      toast({ title: "Sign up failed", description: error.message, variant: "destructive" });
    } else {
      toast({ title: "Account created", description: "Check your email to confirm, then sign in." });
      nav("/login");
    }
  };

  const handleGoogle = async () => {
    const { error } = await signInWithGoogle();
    if (error) {
      toast({ title: "Google sign up failed", description: error.message, variant: "destructive" });
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
        {/* Form (left) */}
        <div className="p-8 md:p-10 order-2 md:order-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight mb-2">Create your account</h1>
          <p className="text-sm text-muted-foreground mb-8">Begin your first staged research run in minutes.</p>

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
            <Field label="Full name" icon={<User className="h-3.5 w-3.5" />}>
              <input
                required value={name} onChange={e => setName(e.target.value)}
                placeholder="Your name"
                className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/50"
              />
            </Field>
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
                placeholder="At least 8 characters"
                className="w-full bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/50"
              />
            </Field>
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow hover:shadow-elegant transition inline-flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Create account <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <p className="text-xs text-muted-foreground text-center mt-6">
            Already have an account?{" "}
            <Link to="/login" className="text-gold hover:underline">Sign in</Link>
          </p>
        </div>

        {/* Brand panel (right) */}
        <div className="relative hidden md:flex flex-col justify-between p-10 bg-gradient-to-br from-card to-muted/40 border-l border-border/60 overflow-hidden order-1 md:order-2">
          <div className="absolute inset-0 -z-10 opacity-60">
            <div className="orb" style={{ background: "var(--gradient-orb-1)", width: 380, height: 380, top: -80, right: -80 }} />
            <div className="orb" style={{ background: "var(--gradient-orb-2)", width: 300, height: 300, bottom: -60, left: -60 }} />
          </div>
          <div className="flex justify-end"><LynxMark size={36} /></div>
          <div>
            <div className="text-xs font-mono uppercase tracking-[0.2em] text-gold mb-3">A digital observatory</div>
            <h2 className="font-display text-4xl font-semibold tracking-tight leading-tight mb-4">
              Begin your first <span className="font-serif-italic text-gold">inquiry</span>.
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">
              From a single research topic to a structured, citation-backed report — generated through a staged AI research pipeline.
            </p>
          </div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Scout · Analyst · Author · Validator
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Signup;
