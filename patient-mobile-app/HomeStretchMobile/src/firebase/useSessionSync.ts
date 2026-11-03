import { useEffect, useRef } from "react";
import {
  startSession,
  updateReps,
  endSession,
  SessionEndStatus,
  SessionStartInfo,
} from "./sessions";

/*
 * Mirrors one exercise set into Firestore:
 *   running false -> true  : create sessions/{id} with status "in_progress"
 *   reps change            : update num_reps / rep_durations
 *   running true  -> false : status "completed" or "interrupted"
 * Writes never block the exercise screen; failures are only logged.
 * Firestore queues writes while offline and sends them later.
 */

type Options = SessionStartInfo & {
  running: boolean;
  reps: number;
  repDurations: number[];
  atypicalFlags: string[];
  // Read when the set ends, to tell a finished set from an interrupted one.
  endStatus: () => SessionEndStatus;
};

const warn = (error: unknown) =>
  console.warn("Firestore session sync failed:", error);

export function useSessionSync(options: Options) {
  const latest = useRef(options);
  latest.current = options;

  const idRef = useRef<Promise<string> | null>(null);
  const startedAtRef = useRef(0);

  const finish = (status: SessionEndStatus) => {
    const pending = idRef.current;
    if (!pending) return;
    idRef.current = null;
    const o = latest.current;
    const durationSec = Math.round((Date.now() - startedAtRef.current) / 1000);
    pending
      .then((id) =>
        endSession(id, {
          status,
          reps: o.reps,
          repDurations: o.repDurations,
          durationSec,
          atypicalFlags: o.atypicalFlags,
        })
      )
      .catch(warn);
  };

  // Start / end
  useEffect(() => {
    const o = latest.current;
    if (options.running && !idRef.current) {
      startedAtRef.current = Date.now();
      const pending = startSession({
        exercise: o.exercise,
        exerciseName: o.exerciseName,
        arm: o.arm,
        targetReps: o.targetReps,
        targetSets: o.targetSets,
      });
      pending.catch(warn);
      idRef.current = pending;
    } else if (!options.running && idRef.current) {
      finish(o.endStatus());
    }
  }, [options.running]);

  // Live rep count
  useEffect(() => {
    const pending = idRef.current;
    if (!pending || !options.running) return;
    const { reps, repDurations } = latest.current;
    pending.then((id) => updateReps(id, reps, repDurations)).catch(warn);
  }, [options.reps]);

  // Leaving the screen mid-set (back button, Complete, tab switch)
  useEffect(() => () => finish(latest.current.endStatus()), []);
}
