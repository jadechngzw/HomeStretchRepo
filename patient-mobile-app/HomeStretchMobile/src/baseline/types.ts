import type { PatientProfile, PendingSession } from '../sync/schema';
import type { Analysis, Reference } from './analysis';
export type Side = 'left' | 'right' | 'both' | 'na';
export type Placement = {
    side: Side;
    wrist: 'left' | 'right';
    face: 'top' | 'inside';
    notes: string;
};
export type Exercise = {
    id: string;
    name: string;
    category?: string;
    instructions: string;
    sets: number;
    reps: number;
    duration: string;
    custom?: boolean;
};
export type Survey = {
    syncedAt?: string;
    day?: string;
    patientId?: string | null;
    id: string;
    phase: 'before' | 'after';
    exerciseId: string | null;
    pain: number;
    symptoms: string;
    regions: string[];
    notes: string;
    recordedAt: string;
};
export type Baseline = {
    id: string;
    exerciseId: string;
    placement: Placement;
    recordedAt: string;
    status: 'awaiting-review' | 'approved';
    approvalMode?: 'automatic-prototype';
    analysis: Analysis;
    reference: Reference;
    surveyId: string;
    rawFile: string;
    deviceName: string;
    protocolSessionId: number;
};
export type Catalog = {
    version: 1;
    patientProfile?: PatientProfile;
    sessionUploads?: PendingSession[];
    customExercises: Exercise[];
    baselines: Baseline[];
    surveys: Survey[];
};
export const DEFAULT_EXERCISES: Exercise[] = [
    { id: 'shoulder-rolls', name: 'Shoulder Rolls', category: 'warm up', instructions: 'Both directions × 10', sets: 1, reps: 10, duration: '~ 1 min' },
    { id: 'knee-extensions', name: 'Gentle Knee Extensions', category: 'warm up', instructions: '2 sets | 10 reps', sets: 2, reps: 10, duration: '~ 3 min' },
    { id: 'sit-to-stand', name: 'Sit to Stand', instructions: '2 sets | 10 reps', sets: 2, reps: 10, duration: '~ 3 min' },
    { id: 'bicep-curls', name: 'Bicep Curls', instructions: '2 sets | 10 reps', sets: 2, reps: 10, duration: '~ 3 min' },
    { id: 'seated-arm-raises', name: 'Seated Arm Raises', instructions: '2 sets | 10 reps', sets: 2, reps: 10, duration: '~ 3 min' },
    { id: 'weight-shifts', name: 'Weight Shifts', instructions: '2 sets | 10 reps', sets: 2, reps: 10, duration: '~ 2 min' },
];
export const sideLabel = (side: Side) => ({ left: 'Left side', right: 'Right side', both: 'Both sides', na: 'Side not applicable' })[side];
export const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
