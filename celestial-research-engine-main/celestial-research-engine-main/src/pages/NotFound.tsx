import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { LynxMark } from "@/components/Brand";
import { ArrowLeft } from "lucide-react";
import { AmbientBackdrop } from "@/components/AmbientBackdrop";

const NotFound = () => {
  const location = useLocation();
  useEffect(() => {
    console.error("404:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6">
      <AmbientBackdrop />
      <div className="text-center max-w-md">
        <LynxMark size={48} animated />
        <div className="font-mono text-xs text-gold uppercase tracking-[0.2em] mt-8 mb-3">404 · off the map</div>
        <h1 className="font-display text-5xl font-semibold tracking-tight mb-3">
          Lost in the <span className="font-serif-italic text-gold">stars</span>.
        </h1>
        <p className="text-muted-foreground mb-8">This page isn't in the observatory's catalog.</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 h-11 px-5 rounded-xl bg-gradient-gold text-gold-foreground font-medium shadow-glow"
        >
          <ArrowLeft className="h-4 w-4" /> Return home
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
