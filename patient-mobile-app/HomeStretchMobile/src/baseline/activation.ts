import { ANALYSIS_VERSION, FEATURES } from './analysis';
import type { Baseline, Catalog } from './types';
export const placementKey = (b: Baseline) => [b.exerciseId, b.placement.side, b.placement.wrist, b.placement.face].join(':');
export function usableReference(b: Baseline): boolean {
  const r = b.reference;
  return r?.version === ANALYSIS_VERSION && Array.isArray(r.acceptedIds) && new Set(r.acceptedIds).size >= 3 &&
    Array.isArray(r.axis) && r.axis.length === 3 && r.axis.every(Number.isFinite) &&
    FEATURES.every(key => {
      const value = r.stats?.[key];
      return value && [value.mean, value.sd, value.lower, value.upper].every(Number.isFinite) && value.sd >= 0 && value.lower <= value.upper;
    });
}
// Temporary prototype policy explicitly requested by the project owner. No clinician approval is implied.
export function autoApprove(data: Catalog): Catalog {
  return {...data, baselines: data.baselines.map(b => b.status === 'awaiting-review' && usableReference(b)
    ? {...b, status: 'approved', approvalMode: 'automatic-prototype'} : b)};
}
export function activeBaselines(data: Catalog, exerciseId: string): Baseline[] {
  const latest = new Map<string, Baseline>();
  for (const b of data.baselines) {
    if (b.exerciseId === exerciseId && b.status === 'approved' && usableReference(b)) latest.set(placementKey(b), b);
  }
  return [...latest.values()];
}
export function isActive(data: Catalog, b: Baseline) {
  return activeBaselines(data, b.exerciseId).some(active => active.id === b.id);
}
