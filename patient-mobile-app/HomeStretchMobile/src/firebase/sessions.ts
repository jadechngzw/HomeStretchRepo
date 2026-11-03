import {
  collection,
  doc,
  setDoc,
  updateDoc,
  serverTimestamp,
} from "firebase/firestore";
import { auth, db } from "./config";

/*
 * One Firestore document per exercise set: sessions/{sessionId}.
 * The clinician dashboard (streamlit-app/app_pages/Patients.py) reads these
 * by patient_id and refreshes every few seconds.
 */

export type SessionEndStatus = "completed" | "interrupted";

export type SessionStartInfo = {
  exercise: string;
  exerciseName: string;
  arm: string | null;
  targetReps: number;
  targetSets: number;
};

export async function startSession(info: SessionStartInfo): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Not signed in");

  const ref = doc(collection(db, "sessions"));
  await setDoc(ref, {
    patient_id: user.uid,
    patient_name: user.displayName ?? null,
    exercise: info.exercise,
    exercise_name: info.exerciseName,
    arm: info.arm,
    target_reps: info.targetReps,
    target_sets: info.targetSets,
    status: "in_progress",
    num_reps: 0,
    rep_durations: [],
    atypical_flags: [],
    source: "ios_app",
    started_at: serverTimestamp(),
    updated_at: serverTimestamp(),
  });
  return ref.id;
}

export function updateReps(
  sessionId: string,
  reps: number,
  repDurations: number[]
) {
  return updateDoc(doc(db, "sessions", sessionId), {
    num_reps: reps,
    rep_durations: repDurations,
    updated_at: serverTimestamp(),
  });
}

export function endSession(
  sessionId: string,
  data: {
    status: SessionEndStatus;
    reps: number;
    repDurations: number[];
    durationSec: number;
    atypicalFlags: string[];
  }
) {
  return updateDoc(doc(db, "sessions", sessionId), {
    status: data.status,
    num_reps: data.reps,
    rep_durations: data.repDurations,
    duration_sec: data.durationSec,
    atypical_flags: data.atypicalFlags,
    ended_at: serverTimestamp(),
    updated_at: serverTimestamp(),
  });
}
