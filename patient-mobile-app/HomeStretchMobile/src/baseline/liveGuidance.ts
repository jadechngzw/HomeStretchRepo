import { analyze, compare } from './analysis';
import type { Analysis, Feature, Reference, Values } from './analysis';
import type { Sample } from '../wearable/protocol';
export type Assessment = { id: number; duration: number; end: number; assessable: boolean; flags: Feature[]; metrics?: Values | null };
export type LiveResult = { reps: Assessment[]; stillness: boolean; placementWarning: boolean; unconfirmedFinal: boolean };
export function paceCue(durations: number[]): 'slow' | 'fast' | 'steady' | 'waiting' {
  if (!durations.length) return 'waiting';
  const recent = durations.slice(-3);
  if (recent.filter(d => d > 3).length > recent.length / 2) return 'slow';
  if (recent.filter(d => d < .8).length > recent.length / 2) return 'fast';
  return 'steady';
}
export function assessAnalysis(analysis: Analysis, reference: Reference, through = Infinity): LiveResult {
  const results = compare(analysis, reference);
  const reps = analysis.reps.filter(rep => rep.end <= through).map(rep => ({...results.find(result => result.id === rep.id)!, duration: rep.duration, end: rep.end}));
  const assessed = reps.filter(rep => rep.assessable);
  return { reps, stillness: analysis.stillness, unconfirmedFinal: analysis.unconfirmedFinal,
    placementWarning: assessed.length >= 3 && assessed.filter(rep => rep.flags.includes('axis_deviation_deg')).length > assessed.length / 2 };
}
// The notebook filter uses future samples. Keep a one-second trailing buffer during live previews.
// Recalculate after an acknowledged STOP using all drained samples for the final summary.
export function assessFrames(frames: Sample[], reference: Reference, final = false): LiveResult {
  const analysis = analyze(frames);
  const elapsed = ((frames[frames.length - 1].ms - frames[0].ms) >>> 0) / 1000;
  return assessAnalysis(analysis, reference, final ? Infinity : elapsed - 1);
}
export const REASONS: Record<Feature, string> = {
  completion_error_deg: 'Return to starting position differed', peak_excursion_deg: 'Movement range differed',
  axis_deviation_deg: 'Movement direction differed', off_axis_energy_fraction: 'More or less off-axis movement',
  gyro_mean_deg_s: 'Average movement speed differed', gyro_peak_deg_s: 'Peak movement speed differed',
  gyro_std_deg_s: 'Movement speed varied differently', accel_magnitude_std_g: 'Acceleration varied differently',
  gyro_high_low_power_ratio: 'Movement frequency pattern differed',
};
