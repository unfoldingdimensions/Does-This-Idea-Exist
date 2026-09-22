"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
import { Compass, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const HEADLINE = "An archive of what exists.";
const WORDS = HEADLINE.split(" ");

export function KineticMasthead({ className }: { className?: string }) {
  const reduce = useReducedMotion();

  const container = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: reduce ? 0 : 0.05, delayChildren: 0.1 },
    },
  };

  const child = {
    hidden: { opacity: 0, y: reduce ? 0 : 18, filter: reduce ? "none" : "blur(6px)" },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: {
        type: "spring" as const,
        damping: 24,
        stiffness: 200,
      },
    },
  };

  return (
    <section className={cn("relative mx-auto max-w-4xl text-center pt-8 pb-4", className)}>
      {/* Editorial datum stamp header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="mb-4 inline-flex flex-wrap items-center justify-center gap-2 rounded-full border border-border/40 bg-background/40 px-3.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground backdrop-blur-md shadow-sm"
      >
        <span className="flex items-center gap-1 text-primary">
          <Compass className="h-3 w-3 animate-[spin_12s_linear_infinite]" />
          <span>VAULT // 01</span>
        </span>
        <span className="text-border">·</span>
        <span className="tabular-nums">LAT 37.77° N · LON 122.42° W</span>
        <span className="text-border">·</span>
        <span className="text-success font-semibold flex items-center gap-1">
          <ShieldCheck className="h-3 w-3" />
          VERIFIED ARCHIVE
        </span>
      </motion.div>

      {/* Kinetic Headline with word stagger */}
      <motion.h1
        variants={container}
        initial="hidden"
        animate="visible"
        className="font-display text-4xl font-bold tracking-tight sm:text-6xl text-foreground flex flex-wrap justify-center gap-x-3.5 gap-y-1"
      >
        {WORDS.map((word, i) => (
          <motion.span
            key={i}
            variants={child}
            className="inline-block relative hover:text-primary transition-colors duration-200"
          >
            {word}
          </motion.span>
        ))}
      </motion.h1>

      {/* Kinetic Subheading */}
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.35 }}
        className="mx-auto mt-4 max-w-[56ch] text-sm md:text-base leading-relaxed text-muted-foreground"
      >
        The archive files what exists — vetted at intake, then re-checked for
        vital signs on a schedule, with every stamp&rsquo;s provenance on the record.
        <span className="block mt-1 text-xs font-mono text-muted-foreground/75">
          Dead is a status, never an erasure. Look closely behind the frosted glass.
        </span>
      </motion.p>
    </section>
  );
}
