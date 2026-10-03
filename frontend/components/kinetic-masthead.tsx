"use client";

import * as React from "react";
import { motion, useReducedMotion } from "motion/react";
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
      {/* No eyebrow above the heading, deliberately. This carried a
          "VAULT // 01 · LAT 37.77° N · LON 122.42° W" stamp with a spinning
          compass: invented coordinates, an invented vault number, and a label
          sitting between the reader and the question the product exists to ask.
          The heading carries its own weight. */}
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
