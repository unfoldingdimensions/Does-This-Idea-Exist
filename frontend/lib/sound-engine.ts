/**
 * Pure Web Audio API micro-sound engine.
 * Synthesizes subtle tactile micro-haptics without external audio files.
 * Default is muted to respect user privacy; toggleable via the AudioToggle control.
 */

class SoundEngine {
  private ctx: AudioContext | null = null;
  private muted = true;
  private listeners = new Set<(muted: boolean) => void>();

  constructor() {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("ideaexists_sound_enabled");
      // Default muted until user explicitly clicks the audio toggle
      this.muted = stored !== "true";
    }
  }

  private initCtx() {
    if (typeof window === "undefined") return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      void this.ctx.resume();
    }
    return this.ctx;
  }

  public isMuted(): boolean {
    return this.muted;
  }

  public setMuted(muted: boolean) {
    this.muted = muted;
    if (typeof window !== "undefined") {
      localStorage.setItem("ideaexists_sound_enabled", muted ? "false" : "true");
    }
    if (!muted) {
      this.initCtx();
      this.playTick();
    }
    this.listeners.forEach((fn) => fn(this.muted));
  }

  public toggleMute(): boolean {
    this.setMuted(!this.muted);
    return this.muted;
  }

  public subscribe(fn: (muted: boolean) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  /** Subtle 10ms mechanical woodblock click for chip selection */
  public playTick() {
    if (this.muted) return;
    const ctx = this.initCtx();
    if (!ctx) return;

    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      const now = ctx.currentTime;
      osc.frequency.setValueAtTime(1100, now);
      osc.frequency.exponentialRampToValueAtTime(320, now + 0.015);

      gain.gain.setValueAtTime(0.045, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.015);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.02);
    } catch {
      // AudioContext failed
    }
  }

  /** Visceral 45ms rubber stamp slam: low 75Hz bass thud + parchment snap */
  public playStamp() {
    if (this.muted) return;
    const ctx = this.initCtx();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;

      // Low frequency paper thud
      const bass = ctx.createOscillator();
      const bassGain = ctx.createGain();
      bass.type = "sine";
      bass.frequency.setValueAtTime(110, now);
      bass.frequency.exponentialRampToValueAtTime(45, now + 0.045);

      bassGain.gain.setValueAtTime(0.09, now);
      bassGain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

      bass.connect(bassGain);
      bassGain.connect(ctx.destination);
      bass.start(now);
      bass.stop(now + 0.055);

      // Snap click
      const snap = ctx.createOscillator();
      const snapGain = ctx.createGain();
      snap.type = "triangle";
      snap.frequency.setValueAtTime(1800, now);
      snap.frequency.exponentialRampToValueAtTime(300, now + 0.012);

      snapGain.gain.setValueAtTime(0.04, now);
      snapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.015);

      snap.connect(snapGain);
      snapGain.connect(ctx.destination);
      snap.start(now);
      snap.stop(now + 0.02);
    } catch {
      // AudioContext failed
    }
  }

  /** Crisp glass harmonic chime for verification confirmation */
  public playChime() {
    if (this.muted) return;
    const ctx = this.initCtx();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      [880, 1320, 1760].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, now + i * 0.02);

        gain.gain.setValueAtTime(0.025 / (i + 1), now + i * 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.02);
        osc.stop(now + 0.2);
      });
    } catch {
      // AudioContext failed
    }
  }

  /** Filtered swoosh for drawer / modal expansion */
  public playSwoosh() {
    if (this.muted) return;
    const ctx = this.initCtx();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const filter = ctx.createBiquadFilter();
      const gain = ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(240, now);
      osc.frequency.exponentialRampToValueAtTime(520, now + 0.04);

      filter.type = "bandpass";
      filter.frequency.setValueAtTime(450, now);
      filter.Q.setValueAtTime(2, now);

      gain.gain.setValueAtTime(0.03, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.06);
    } catch {
      // AudioContext failed
    }
  }

  /** Crisp 25ms radar blip */
  public playBlip() {
    if (this.muted) return;
    const ctx = this.initCtx();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(800, now + 0.025);

      gain.gain.setValueAtTime(0.02, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.025);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.03);
    } catch {
      // AudioContext failed
    }
  }
}

export const sound = new SoundEngine();
