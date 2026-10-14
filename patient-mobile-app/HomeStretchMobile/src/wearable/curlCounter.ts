// Streaming adaptation of session_pipeline/motion.py and exercises.json:
// 2 Hz live low-pass, 0.6 g excursion, 0.5–6 s movement windows; >=0.8 s between reps. A causal second-order
// Butterworth replaces sosfiltfilt. A baseline-return cycle counts the first
// full curl, unlike offline peak-to-peak boundaries. No form classification.
export type RepEvent = { count: number; durationSec: number; endedAtMs: number };
export class CurlCounter {
  count = 0;
  ready = false;
  private lastMs?: number;
  private baseline?: number;
  private warmup: { ms: number; y: number }[] = [];
  private x1 = 0; private x2 = 0; private y1 = 0; private y2 = 0;
  private initialized = false;
  private phase: 'rest' | 'moving' | 'return' | 'rearm' = 'rest';
  private began = 0;
  private direction = 1;
  private peak = 0;
  private lastEvent = -Infinity;
  private observed = 0;
  private missing = 0;
  noteMissing(count = 1) {
    if (this.phase === 'moving' || this.phase === 'return') this.missing += count;
  }
  discardPartial() {
    // Preserve a known baseline across a brief loss, but wait for a return
    // before arming another curl. Long timestamp gaps still recalibrate.
    if (this.baseline !== undefined) this.phase = 'rearm';
  }
  resetMovement() {
    this.ready = false; this.baseline = undefined; this.warmup = [];
    this.initialized = false; this.phase = 'rest'; this.lastMs = undefined;
  }
  add(ms: number, y: number): RepEvent | null {
    if (!Number.isFinite(ms) || !Number.isFinite(y)) { this.resetMovement(); return null; }
    if (this.lastMs !== undefined && (ms <= this.lastMs || ms - this.lastMs > 60)) this.resetMovement();
    const dt = this.lastMs === undefined ? 0.02 : (ms - this.lastMs) / 1000;
    this.lastMs = ms;
    if (!this.initialized) { this.x1 = this.x2 = this.y1 = this.y2 = y; this.initialized = true; }
    const k = Math.tan(2 * Math.PI * dt), n = 1 / (1 + Math.SQRT2 * k + k * k);
    const b = k * k * n, a1 = 2 * (k * k - 1) * n, a2 = (1 - Math.SQRT2 * k + k * k) * n;
    const filtered = b * (y + 2 * this.x1 + this.x2) - a1 * this.y1 - a2 * this.y2;
    this.x2 = this.x1; this.x1 = y; this.y2 = this.y1; this.y1 = filtered;
    if (this.baseline === undefined) {
      this.warmup.push({ ms, y });
      while (this.warmup.length && ms - this.warmup[0].ms > 2000) this.warmup.shift();
      if (this.warmup.length >= 30 && ms - this.warmup[0].ms >= 1900) {
        const values = this.warmup.map(s => s.y);
        if (Math.max(...values) - Math.min(...values) < 0.12) {
          this.baseline = values.reduce((a, b) => a + b, 0) / values.length;
          this.ready = true; this.warmup = [];
        }
      }
      return null;
    }
    const delta = filtered - this.baseline;
    if (this.phase === 'rearm') {
      if (Math.abs(delta) <= 0.14) this.phase = 'rest';
      return null;
    }
    if (this.phase === 'rest') {
      if (Math.abs(delta) > 0.18) {
        this.phase = 'moving'; this.began = ms; this.direction = Math.sign(delta); this.peak = Math.abs(delta); this.observed = 1; this.missing = 0;
      }
      return null;
    }
    this.observed++;
    const excursion = delta * this.direction;
    this.peak = Math.max(this.peak, excursion);
    if (this.peak >= 0.6) this.phase = 'return';
    if (ms - this.began > 6000) { this.phase = 'rest'; return null; }
    if (excursion <= 0.14) {
      const durationSec = (ms - this.began) / 1000;
      const completed = this.phase === 'return' && durationSec >= 0.5 && durationSec <= 6 && ms - this.lastEvent >= 800 &&
        this.missing / (this.missing + this.observed) <= 0.1;
      this.phase = 'rest';
      if (completed) { this.count++; this.lastEvent = ms; return { count: this.count, durationSec, endedAtMs: ms }; }
    }
    return null;
  }
}
