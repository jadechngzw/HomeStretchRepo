// Patient-specific nine-feature notebook port. Native capture uses 25 Hz.
// Versioned separately from legacy curl counting; no anatomical angle claims.
import type { Sample } from '../wearable/protocol';
export const ANALYSIS_VERSION = 'patient-nine-25hz-v1';
export const FEATURES = ['completion_error_deg', 'peak_excursion_deg', 'axis_deviation_deg',
    'off_axis_energy_fraction', 'gyro_mean_deg_s', 'gyro_peak_deg_s', 'gyro_std_deg_s',
    'accel_magnitude_std_g', 'gyro_high_low_power_ratio'] as const;
export type Feature = typeof FEATURES[number];
export type Values = Record<Feature, number>;
export const LABELS: Record<Feature, string> = {
    completion_error_deg: 'Return-to-start orientation error (°)', peak_excursion_deg: 'Maximum orientation excursion (°)',
    axis_deviation_deg: 'Movement-axis deviation (°)', off_axis_energy_fraction: 'Off-axis rotational energy fraction',
    gyro_mean_deg_s: 'Mean angular speed (°/s)', gyro_peak_deg_s: 'Peak angular speed (°/s)',
    gyro_std_deg_s: 'Angular-speed variability (°/s)', accel_magnitude_std_g: 'Acceleration-magnitude variability (g)',
    gyro_high_low_power_ratio: 'High/low frequency power ratio',
};
type Vec = [
    number,
    number,
    number
];
type Quat = [
    number,
    number,
    number,
    number
]; // x,y,z,w
export type Rep = {
    id: number;
    start: number;
    end: number;
    duration: number;
    features: Values;
    moment: number[];
    eligible: boolean;
    reason?: string;
};
export type Analysis = {
    version: string;
    rate: number;
    stillness: boolean;
    reps: Rep[];
    unconfirmedFinal: boolean;
    warnings: string[];
};
export type Reference = {
    version: string;
    axis: Vec;
    acceptedIds: number[];
    stats: Record<Feature, {
        mean: number;
        sd: number;
        lower: number;
        upper: number;
    }>;
};
const mean = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length;
const sd = (v: number[], sample = false) => Math.sqrt(v.reduce((s, x) => s + (x - mean(v)) ** 2, 0) / (v.length - Number(sample)));
const median = (v: number[]) => { const s = [...v].sort((a, b) => a - b), k = Math.floor(s.length / 2); return s.length % 2 ? s[k] : (s[k - 1] + s[k]) / 2; };
const norm = (v: number[]) => Math.hypot(...v);
const dot = (a: number[], b: number[]) => a.reduce((s, x, i) => s + x * b[i], 0);
const cross = (a: Vec, b: Vec): Vec => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const mul = (a: Quat, b: Quat): Quat => [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0], a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
const inv = (q: Quat): Quat => [-q[0], -q[1], -q[2], q[3]];
const rotate = (q: Quat, v: Vec): Vec => mul(mul(q, [...v, 0]), inv(q)).slice(0, 3) as Vec;
const angle = (q: Quat) => 2 * Math.atan2(norm(q.slice(0, 3)), Math.abs(q[3])) * 180 / Math.PI;
const rotvec = (v: Vec): Quat => { const n = norm(v), s = n < 1e-12 ? .5 : Math.sin(n / 2) / n; return [v[0] * s, v[1] * s, v[2] * s, Math.cos(n / 2)]; };
const SOS = [[.022870207716290964, .04574041543258193, .022870207716290964, -.602033202257445, .12355934398734861], [1, 2, 1, -.8099502989391327, .5115897646941698]];
const ZI = [[.15253965872246839, .0011966796902094226], [.8245901335612413, -.3361798982554107]];
function filter(v: number[]) {
    const first = v[0], z = ZI.map(row => row.map(x => x * first));
    return v.map(x => { for (let i = 0; i < 2; i++) {
        const [b0, b1, b2, a1, a2] = SOS[i], y = b0 * x + z[i][0];
        z[i][0] = b1 * x - a1 * y + z[i][1];
        z[i][1] = b2 * x - a2 * y;
        x = y;
    } return x; });
}
function smooth(v: number[]) {
    const n = 15;
    if (v.length <= n)
        throw new Error('Not enough movement data. Record again.');
    const padded = [...v.slice(1, n + 1).reverse().map(x => 2 * v[0] - x), ...v, ...v.slice(-n - 1, -1).reverse().map(x => 2 * v[v.length - 1] - x)];
    return filter(filter(padded).reverse()).reverse().slice(n, -n);
}
function powerRatio(v: number[]) {
    const n = v.length, avg = mean(v);
    let lo = 0, hi = 0;
    for (let k = 0; k <= Math.floor(n / 2); k++) {
        const freq = k * 25 / n;
        if (!((freq >= .1 && freq <= 2) || (freq >= 3 && freq <= 8)))
            continue;
        let re = 0, im = 0;
        for (let j = 0; j < n; j++) {
            const x = (v[j] - avg) * (.5 - .5 * Math.cos(2 * Math.PI * j / n));
            re += x * Math.cos(2 * Math.PI * k * j / n);
            im -= x * Math.sin(2 * Math.PI * k * j / n);
        }
        const power = 2 * (re * re + im * im) / (n / 2) ** 2;
        if (freq <= 2)
            lo += power;
        else
            hi += power;
    }
    return lo > 1e-12 ? hi / lo : NaN;
}
function moment(v: Vec[]) { const m = Array(9).fill(0) as number[]; for (const a of v)
    for (let i = 0; i < 3; i++)
        for (let j = 0; j < 3; j++)
            m[i * 3 + j] += a[i] * a[j]; const energy = m[0] + m[4] + m[8]; return energy > 1e-12 ? m.map(x => x / energy) : m.map(() => NaN); }
// Symmetric Jacobi eigensolver; deterministic and robust to a dominant axis perpendicular to x.
function axis(m: number[]): Vec {
    const a = [...m], v = [1, 0, 0, 0, 1, 0, 0, 0, 1];
    if (!a.every(Number.isFinite))
        throw new Error('Too little rotation to establish a reference axis.');
    for (let iter = 0; iter < 40; iter++) {
        let p = 0, q = 1;
        for (const [i, j] of [[0, 2], [1, 2]])
            if (Math.abs(a[i * 3 + j]) > Math.abs(a[p * 3 + q])) {
                p = i;
                q = j;
            }
        if (Math.abs(a[p * 3 + q]) < 1e-14)
            break;
        const theta = .5 * Math.atan2(2 * a[p * 3 + q], a[q * 3 + q] - a[p * 3 + p]), c = Math.cos(theta), s = Math.sin(theta);
        for (let k = 0; k < 3; k++) {
            const x = a[k * 3 + p], y = a[k * 3 + q];
            a[k * 3 + p] = c * x - s * y;
            a[k * 3 + q] = s * x + c * y;
        }
        for (let k = 0; k < 3; k++) {
            const x = a[p * 3 + k], y = a[q * 3 + k];
            a[p * 3 + k] = c * x - s * y;
            a[q * 3 + k] = s * x + c * y;
        }
        for (let k = 0; k < 3; k++) {
            const x = v[k * 3 + p], y = v[k * 3 + q];
            v[k * 3 + p] = c * x - s * y;
            v[k * 3 + q] = s * x + c * y;
        }
    }
    let k = 0;
    for (let i = 1; i < 3; i++)
        if (a[i * 3 + i] > a[k * 3 + k])
            k = i;
    return [v[k], v[3 + k], v[6 + k]];
}
function withDirection(rep: Rep, reference: Vec): Values {
    const own = axis(rep.moment), projected = [0, 1, 2].map(i => dot(rep.moment.slice(i * 3, i * 3 + 3), reference));
    return { ...rep.features, axis_deviation_deg: Math.acos(clamp(Math.abs(dot(own, reference)), 0, 1)) * 180 / Math.PI,
        off_axis_energy_fraction: clamp(1 - dot(reference, projected), 0, 1) };
}
export function analyze(frames: Sample[]): Analysis {
    if (!frames.length || new Set(frames.map(f => f.session)).size !== 1)
        throw new Error('Record one complete session before reviewing.');
    if (frames.some(f => !f.valid))
        throw new Error('Some watch samples were invalid. Please record again.');
    const streams = [1, 2].map(type => {
        const f = frames.filter(s => s.type === type);
        if (f.length < 75)
            throw new Error('Not enough usable data from both movement sensors. Record again.');
        let elapsed = 0;
        const t = f.map((s, i) => { if (i) {
            const dt = (s.ms - f[i - 1].ms) >>> 0;
            if (!dt || dt > 85)
                throw new Error('Movement data has gaps. Please record again.');
            elapsed += dt;
        } return elapsed / 1000; });
        const delta = t.slice(1).map((x, i) => x - t[i]);
        if (Math.abs(1 / median(delta) - 25) > 2.5)
            throw new Error('This baseline needs a 25 Hz recording. Record again with this app.');
        const offset = ((f[0].ms - frames[0].ms) >>> 0) / 1000;
        return { t: t.map(x => x + offset), v: f.map(s => [s.x, s.y, s.z].map(x => x * (type === 1 ? .000061 : .00875)) as Vec) };
    });
    const start = Math.max(...streams.map(s => s.t[0])), end = Math.min(...streams.map(s => s.t.at(-1)!));
    const t = Array.from({ length: Math.floor((end - start) * 25 + 1e-7) + 1 }, (_, i) => start + i / 25);
    if (t.length < 76)
        throw new Error('Recording was too short. Please record again.');
    const aligned = streams.map(stream => { let j = 0; return t.map(x => { while (j < stream.t.length - 2 && stream.t[j + 1] < x)
        j++; const f = (x - stream.t[j]) / (stream.t[j + 1] - stream.t[j]); return stream.v[j].map((v, k) => v + f * (stream.v[j + 1][k] - v)) as Vec; }); });
    const [accRaw, gyroRaw] = aligned, lead = t.map(x => x < t[0] + 2), leadAcc = accRaw.filter((_, i) => lead[i]), leadGyro = gyroRaw.filter((_, i) => lead[i]);
    const stillness = sd(leadAcc.map(norm)) <= .03 && Math.max(...leadGyro.map(norm)) <= 5;
    if (stillness) {
        const bias = [0, 1, 2].map(k => mean(leadGyro.map(v => v[k])));
        gyroRaw.forEach(v => v.forEach((_, k) => v[k] -= bias[k]));
    }
    const filtered = aligned.map(v => { const cols = [0, 1, 2].map(k => smooth(v.map(x => x[k]))); return v.map((_, i) => cols.map(c => c[i]) as Vec); });
    const [acc, gyro] = filtered, [x, y, z] = acc[0];
    const roll = Math.atan2(y, z), pitch = Math.atan2(-x, Math.hypot(y, z));
    let r = mul(rotvec([0, pitch, 0]), rotvec([roll, 0, 0]));
    const r0 = r, quats: Quat[] = [r], angles = [0];
    for (let i = 1; i < t.length; i++) {
        const w = gyro[i].map((v, k) => (v + gyro[i - 1][k]) / 2 * Math.PI / 180) as Vec, n = norm(acc[i]);
        if (n >= .85 && n <= 1.15) {
            const correction = cross(acc[i].map(v => v / n) as Vec, rotate(inv(r), [0, 0, 1]));
            w.forEach((_, k) => w[k] += .5 * correction[k]);
        }
        r = mul(r, rotvec(w.map(v => v * (t[i] - t[i - 1])) as Vec));
        const rn = norm(r);
        r = r.map(v => v / rn) as Quat;
        quats.push(r);
        angles.push(angle(mul(inv(r0), r)));
    }
    // Python round(2.5) is 2 (banker's rounding), matching the notebook's 0.1 s window.
    const excursion = angles.map((_, i) => mean(angles.slice(Math.max(0, i - 1), i + 1))), speed = gyro.map(norm);
    let mode = 'seek', low: number | undefined, high: number | undefined, a: number | undefined;
    const candidates: [
        number,
        number
    ][] = [];
    for (let i = 0; i < t.length; i++) {
        if (lead[i])
            continue;
        if (low === undefined) {
            low = i;
            continue;
        }
        if (mode === 'seek' || mode === 'rise') {
            if (excursion[i] < excursion[low])
                low = i;
            if (mode === 'seek' && excursion[i] - excursion[low] >= 15) {
                a = low;
                high = i;
                mode = 'rise';
            }
            else if (mode === 'rise') {
                if (high === undefined || excursion[i] > excursion[high])
                    high = i;
                if (excursion[high!] - excursion[i] >= 8) {
                    low = i;
                    mode = 'fall';
                }
            }
        }
        else {
            if (excursion[i] < excursion[low])
                low = i;
            if (excursion[i] - excursion[low] >= 8) {
                candidates.push([a!, low]);
                a = low;
                high = i;
                mode = 'rise';
            }
        }
    }
    if (candidates.length) {
        const rest = speed.filter((_, i) => lead[i]), med = median(rest), onset = Math.max(10, med + 6 * median(rest.map(x => Math.abs(x - med))));
        const [a, b] = candidates[0];
        for (let k = a; k <= b - 3 + 1; k++)
            if (speed.slice(k, k + 3).every(x => x > onset)) {
                candidates[0] = [Math.max(a, k - 1), b];
                break;
            }
    }
    if (a !== undefined && mode === 'fall' && high !== undefined && excursion[high] - excursion[a] >= 15) {
        let settled: number | undefined;
        for (let i = high + 1; i < t.length; i++) {
            if (Math.abs(excursion[i] - excursion[a]) <= 15 && excursion[high] - excursion[i] >= 8 && speed[i] <= 15) {
                settled ??= i;
                if (t[i] - t[settled] >= .5) {
                    candidates.push([a, settled]);
                    a = undefined;
                    break;
                }
            }
            else
                settled = undefined;
        }
    }
    const vectors = gyro.map((v, i) => rotate(mul(inv(quats[0]), quats[i]), v));
    const reps: Rep[] = [];
    for (const [a, b] of candidates) {
        const dur = t[b] - t[a], exc = excursion.slice(a, b + 1);
        if (dur < .6 || dur > 8 || Math.max(...exc) - Math.min(...exc) < 15)
            continue;
        const speeds = speed.slice(a, b + 1), m = moment(vectors.slice(a, b + 1));
        const features: Values = { completion_error_deg: angle(mul(inv(quats[a]), quats[b])), peak_excursion_deg: Math.max(...quats.slice(a, b + 1).map(q => angle(mul(inv(quats[a]), q)))), axis_deviation_deg: 0, off_axis_energy_fraction: 0,
            gyro_mean_deg_s: mean(speeds), gyro_peak_deg_s: Math.max(...speeds), gyro_std_deg_s: sd(speeds), accel_magnitude_std_g: sd(acc.slice(a, b + 1).map(norm)), gyro_high_low_power_ratio: powerRatio(gyroRaw.slice(a, b + 1).map(norm)) };
        const eligible = Object.values(features).every(Number.isFinite) && m.every(Number.isFinite);
        reps.push({ id: reps.length + 1, start: t[a], end: t[b], duration: dur, features, moment: m, eligible, ...(!eligible ? { reason: 'Not enough usable movement to calculate every feature.' } : {}) });
    }
    return { version: ANALYSIS_VERSION, rate: 25, stillness, reps, unconfirmedFinal: a !== undefined, warnings: [...(!stillness ? ['Initial stillness check failed. No gyro bias correction was applied.'] : []), ...(a !== undefined ? ['An unconfirmed final movement was excluded.'] : [])] };
}
export function buildReference(analysis: Analysis, ids: number[]): Reference {
    if (new Set(ids).size !== ids.length || ids.length < 3)
        throw new Error('Keep at least three different complete repetitions.');
    const selected = ids.map(id => analysis.reps.find(r => r.id === id));
    if (selected.some(r => !r?.eligible))
        throw new Error('Only complete repetitions with all nine features can be kept.');
    const reps = selected as Rep[], m = Array.from({ length: 9 }, (_, k) => mean(reps.map(r => r.moment[k]))), referenceAxis = axis(m), values = reps.map(r => withDirection(r, referenceAxis));
    const stats = {} as Reference['stats'];
    for (const key of FEATURES) {
        const v = values.map(r => r[key]), avg = mean(v), std = sd(v, true), max = key === 'axis_deviation_deg' ? 90 : key === 'off_axis_energy_fraction' ? 1 : ['completion_error_deg', 'peak_excursion_deg'].includes(key) ? 180 : Infinity;
        stats[key] = { mean: avg, sd: std, lower: Math.max(0, avg - 3 * std), upper: Math.min(max, avg + 3 * std) };
    }
    return { version: ANALYSIS_VERSION, axis: referenceAxis, acceptedIds: [...ids], stats };
}
export function compare(analysis: Analysis, reference: Reference) {
    if (reference.version !== analysis.version)
        throw new Error('Baseline processing version does not match this recording.');
    return analysis.reps.map(rep => { if (!rep.eligible)
        return { id: rep.id, assessable: false, flags: [] as Feature[] }; const values = withDirection(rep, reference.axis); return { id: rep.id, assessable: true, flags: FEATURES.filter(key => values[key] < reference.stats[key].lower || values[key] > reference.stats[key].upper) }; });
}
