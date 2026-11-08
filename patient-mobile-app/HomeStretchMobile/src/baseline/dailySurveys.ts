import type { Catalog, Survey } from './types';

export function localDay(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function dailySurvey(data: Catalog, phase: Survey['phase'], day = localDay()) {
  return data.surveys.find(s => s.day === day && s.phase === phase &&
    s.patientId === (data.patientProfile?.id ?? null));
}
