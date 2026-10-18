// src/wearable/useLiveGuidance.ts
import { useEffect, useRef, useState } from "react";
import { session } from "./useCurlSession";

// Mirror your Python constants
const REP_GOAL = 10;
const MIN_REP_DURATION = 0.8;
const MAX_REP_DURATION = 3.0;
const MAJORITY_THRESHOLD = 0.5;
const ATYPICAL_THRESHOLD = 0.4;
const HR_ACTIVE_MAX = 160;
const PPG_COVERAGE_MIN = 70;

export type GuidanceState = "IDLE_PRE" | "EXERCISING" | "PAUSED" | "IDLE_POST";

export interface GuidanceSnapshot {
  state: GuidanceState;
  message: string;
  pauseReason: string | null;
  atypicalFlags: string[];
  repCount: number;
}

export function useLiveGuidance() {
  const [guidance, setGuidance] = useState<GuidanceSnapshot>({
    state: "IDLE_PRE",
    message: "Ready to begin",
    pauseReason: null,
    atypicalFlags: [],
    repCount: 0,
  });

  // Use refs so the onRep callback always sees current values
  const stateRef = useRef<GuidanceState>("IDLE_PRE");
  const durationsRef = useRef<number[]>([]);
  const atypicalFlagsRef = useRef<string[]>([]);

  const update = (patch: Partial<GuidanceSnapshot>) => {
    setGuidance(prev => {
      const next = { ...prev, ...patch };
      stateRef.current = next.state;
      return next;
    });
  };

  useEffect(() => {
    // Reset when a new set starts
    stateRef.current = "IDLE_PRE";
    durationsRef.current = [];
    atypicalFlagsRef.current = [];
    setGuidance({ state: "IDLE_PRE", message: "Ready to begin",
      pauseReason: null, atypicalFlags: [], repCount: 0 });

    const unsubRep = session.onRep((rep) => {
      durationsRef.current.push(rep.durationSec);
      const repCount = rep.count;
      const durations = durationsRef.current;
      const currentState = stateRef.current;

      // IDLE_PRE → EXERCISING on first rep
      if (currentState === "IDLE_PRE") {
        update({ state: "EXERCISING", message: `Rep ${repCount} — keep going!`, repCount });
        return;
      }

      if (currentState !== "EXERCISING") return;

      // Check rep timing (majority threshold)
      const slowReps = durations.filter(d => d > MAX_REP_DURATION).length;
      const fastReps = durations.filter(d => d < MIN_REP_DURATION).length;
      if (slowReps / durations.length > MAJORITY_THRESHOLD) {
        update({ state: "PAUSED", pauseReason: "Most reps are too slow — try to maintain a steady pace",
          message: "Pause: reps too slow", repCount });
        return;
      }
      if (fastReps / durations.length > MAJORITY_THRESHOLD) {
        update({ state: "PAUSED", pauseReason: "Most reps are too fast — slow down for better form",
          message: "Pause: reps too fast", repCount });
        return;
      }

      // Session complete
      if (repCount >= REP_GOAL) {
        update({ state: "IDLE_POST", message: `Great work! ${repCount} reps completed.`,
          pauseReason: null, atypicalFlags: atypicalFlagsRef.current, repCount });
        return;
      }

      update({ state: "EXERCISING", message: `Rep ${repCount} of ${REP_GOAL}`, repCount });
    });

    // Watch for session ending
    const unsubSession = session.subscribe(() => {
      const snap = session.getSnapshot();
      if (snap.phase === "ended" || snap.phase === "interrupted") {
        if (stateRef.current !== "IDLE_POST") {
          update({ state: "IDLE_POST",
            message: snap.phase === "ended" ? "Set complete" : "Set interrupted",
            atypicalFlags: atypicalFlagsRef.current });
        }
      }
    });

    return () => { unsubRep(); unsubSession(); };
  }, []);

  return guidance;
}