"use client";

import * as React from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "motion/react";
import { Sun, Moon, Sunrise, Sunset } from "lucide-react";
import { sound } from "@/lib/sound-engine";
import { cn } from "@/lib/utils";

export type SkyPhase = "dawn" | "noon" | "sunset" | "aurora" | "scroll";

interface SkyStageProps {
  className?: string;
}

export function SkyStage({ className }: SkyStageProps) {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const [phase, setPhase] = React.useState<SkyPhase>("scroll");

  // Scroll mapping for auto-scroll mode
  const scrollSunY = useTransform(scrollYProgress, [0, 1], ["6vh", "42vh"]);
  const scrollSunScale = useTransform(scrollYProgress, [0, 1], [1.1, 0.88]);
  const scrollEveningWash = useTransform(scrollYProgress, [0, 0.45, 1], [0, 0.5, 1]);

  // Particle Canvas for stardust
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);

  React.useEffect(() => {
    if (reduce) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const onResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", onResize);

    const count = 36;
    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 1.8 + 0.6,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      alpha: Math.random() * 0.6 + 0.2,
    }));

    let mouseX = width / 2;
    let mouseY = height / 2;
    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    window.addEventListener("mousemove", onMouseMove);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around bounds
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Subtle mouse repulsion
        const dx = p.x - mouseX;
        const dy = p.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120 && dist > 0) {
          const force = (120 - dist) / 120;
          p.x += (dx / dist) * force * 1.5;
          p.y += (dy / dist) * force * 1.5;
        }

        ctx.fillStyle = `rgba(255, 235, 200, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
    };
  }, [reduce]);

  const selectPhase = (p: SkyPhase) => {
    sound.playTick();
    setPhase(p);
  };

  return (
    <>
    <div
      aria-hidden
      className={cn(
        "pointer-events-none fixed inset-0 z-[-1] overflow-hidden select-none transition-opacity duration-700",
        className,
      )}
    >
      {/* Dynamic Stardust Canvas */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-0 opacity-40 dark:opacity-60"
      />

      {/* Atmospheric Wash Layers */}
      {/* 1. Dawn / Morning Gold */}
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-1000 bg-gradient-to-b from-amber-100/50 via-amber-200/25 to-transparent dark:from-indigo-950/40 dark:via-purple-950/20",
          phase === "dawn" ? "opacity-100" : phase === "scroll" ? "opacity-80" : "opacity-0",
        )}
      />

      {/* 2. High Noon Radiant Glare */}
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-1000 bg-gradient-to-b from-yellow-50/70 via-sky-100/30 to-transparent dark:from-slate-900/60 dark:via-indigo-900/30",
          phase === "noon" ? "opacity-100" : "opacity-0",
        )}
      />

      {/* 3. Sunset Cadmium Evening */}
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-1000 bg-gradient-to-b from-orange-200/60 via-rose-300/30 to-amber-100/20 dark:from-purple-950/70 dark:via-indigo-950/40",
          phase === "sunset" ? "opacity-100" : "opacity-0",
        )}
      />

      {/* 4. Midnight Aurora Shift */}
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-1000 bg-gradient-to-b from-emerald-950/30 via-indigo-950/60 to-slate-950/80",
          phase === "aurora" ? "opacity-100" : "opacity-0",
        )}
      />

      {/* Auto-scroll evening wash crossfade */}
      {phase === "scroll" && (
        <motion.div
          style={{ opacity: scrollEveningWash }}
          className="absolute inset-0 bg-gradient-to-b from-amber-300/20 via-orange-400/15 to-transparent transition-colors duration-500"
        />
      )}

      {/* Celestial Orb (Sun / Moon) with multi-frequency atmospheric diffusion */}
      <motion.div
        style={
          phase === "scroll" && !reduce
            ? { y: scrollSunY, scale: scrollSunScale }
            : phase === "dawn"
              ? { y: "4vh", scale: 1.1 }
              : phase === "noon"
                ? { y: "-2vh", scale: 1.2 }
                : phase === "sunset"
                  ? { y: "32vh", scale: 0.95 }
                  : { y: "38vh", scale: 0.85 }
        }
        transition={{ type: "spring", stiffness: 90, damping: 22 }}
        className="pointer-events-none absolute left-1/2 -translate-x-1/2 -top-8 flex h-96 w-96 items-center justify-center rounded-full"
      >
        {/* Soft atmospheric corona */}
        <div className="absolute inset-0 rounded-full bg-radial from-amber-200/40 via-orange-400/15 to-transparent blur-2xl dark:from-indigo-300/25 dark:via-purple-400/10 dark:to-transparent animate-[pulse_6s_ease-in-out_infinite]" />
        {/* Inner radiant aura (diffused so text over it remains pristine) */}
        <div className="h-44 w-44 rounded-full bg-radial from-amber-100/70 via-orange-200/40 to-transparent blur-xl dark:from-slate-100/50 dark:via-indigo-200/25 dark:to-transparent" />
      </motion.div>

      {/* Mountain Horizon Silhouette Layers (SVG Parallax) */}
      <div className="sky-silhouette sky-silhouette--mountain opacity-85 dark:opacity-90" />
    </div>

    {/* Interactive Time Scrubber Dock (Floating bottom-right, accessible and above content) */}
    <aside
      aria-label="Celestial sky orbit"
      className="fixed bottom-3 right-3 z-40 flex items-center gap-1 rounded-full border border-border/50 bg-background/70 p-1 backdrop-blur-xl shadow-xl transition-all hover:scale-105"
    >
      <span className="pl-2 pr-1 font-mono text-[9px] font-bold uppercase tracking-widest text-muted-foreground hidden sm:inline">
        Sky Orbit
      </span>
      <button
        type="button"
        onClick={() => selectPhase("dawn")}
        aria-label="Dawn atmosphere"
        title="Dawn"
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs transition-colors",
          phase === "dawn" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Sunrise className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={() => selectPhase("noon")}
        aria-label="High Noon atmosphere"
        title="Noon"
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs transition-colors",
          phase === "noon" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Sun className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={() => selectPhase("sunset")}
        aria-label="Sunset Cadmium atmosphere"
        title="Sunset"
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs transition-colors",
          phase === "sunset" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Sunset className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={() => selectPhase("aurora")}
        aria-label="Midnight Aurora atmosphere"
        title="Midnight Aurora"
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded-full text-xs transition-colors",
          phase === "aurora" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Moon className="h-3 w-3" />
      </button>
      <button
        type="button"
        onClick={() => selectPhase("scroll")}
        aria-label="Scroll-linked automatic orbit"
        title="Auto Scroll-Linked"
        className={cn(
          "px-2 h-6 flex items-center justify-center rounded-full font-mono text-[9px] uppercase tracking-wider transition-colors",
          phase === "scroll" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:text-foreground",
        )}
      >
        Auto
      </button>
    </aside>
    </>
  );
}

