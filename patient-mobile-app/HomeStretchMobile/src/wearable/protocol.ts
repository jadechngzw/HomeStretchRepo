export const UUID = {
  service: '7bfa0001-6e4d-4b9d-923b-5d234081a100',
  control: '7bfa0002-6e4d-4b9d-923b-5d234081a100',
  status: '7bfa0003-6e4d-4b9d-923b-5d234081a100',
  samples: '7bfa0004-6e4d-4b9d-923b-5d234081a100',
};
const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
export function encode(bytes: Uint8Array): string {
  let result = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);
    result += alphabet[(n >>> 18) & 63] + alphabet[(n >>> 12) & 63] +
      (i + 1 < bytes.length ? alphabet[(n >>> 6) & 63] : '=') +
      (i + 2 < bytes.length ? alphabet[n & 63] : '=');
  }
  return result;
}
export function decode(value: string | null): Uint8Array {
  if (!value || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value))
    throw new Error('The watch sent an unreadable message.');
  const bytes: number[] = [];
  for (let i = 0; i < value.length; i += 4) {
    const n = (alphabet.indexOf(value[i]) << 18) | (alphabet.indexOf(value[i + 1]) << 12) |
      (Math.max(0, alphabet.indexOf(value[i + 2])) << 6) | Math.max(0, alphabet.indexOf(value[i + 3]));
    bytes.push((n >>> 16) & 255);
    if (value[i + 2] !== '=') bytes.push((n >>> 8) & 255);
    if (value[i + 3] !== '=') bytes.push(n & 255);
  }
  return Uint8Array.from(bytes);
}
export function command(opcode: number, request: number, argument: number, session: number) {
  const bytes = new Uint8Array(12), view = new DataView(bytes.buffer);
  bytes[0] = 3; bytes[1] = opcode;
  view.setUint16(2, request, true); view.setUint32(4, argument, true); view.setUint32(8, session, true);
  return encode(bytes);
}
export type WatchStatus = { state: number; reason: number; mask: number; session: number; request: number; charger: number; generated: number; dropped: number };
export function status(value: string | null): WatchStatus {
  const bytes = decode(value);
  if (bytes.length !== 20 || bytes[0] !== 3 || bytes[1] > 2) throw new Error('This watch needs compatible VitalWave firmware.');
  const v = new DataView(bytes.buffer);
  return { state: bytes[1], reason: bytes[2], mask: bytes[3], session: v.getUint32(4, true),
    request: v.getUint16(8, true), charger: v.getUint16(10, true), generated: v.getUint32(12, true), dropped: v.getUint32(16, true) };
}
export type Sample = { type: number; session: number; sequence: number; ms: number; x: number; y: number; z: number; valid: boolean };
export function samples(value: string | null): Sample[] {
  const bytes = decode(value);
  if (!bytes.length || bytes.length > 240 || bytes.length % 20) throw new Error('A movement packet was incomplete.');
  const v = new DataView(bytes.buffer), result: Sample[] = [];
  for (let i = 0; i < bytes.length; i += 20) {
    if (bytes[i] !== 3 || bytes[i + 1] < 1 || bytes[i + 1] > 7) throw new Error('An unexpected movement packet arrived.');
    const validity = v.getInt16(i + 18, true);
    if (validity !== 0 && validity !== 1) throw new Error('A movement packet had invalid quality information.');
    result.push({ type: bytes[i + 1], session: v.getUint32(i + 2, true), sequence: v.getUint16(i + 6, true),
      ms: v.getUint32(i + 8, true), x: v.getInt16(i + 12, true), y: v.getInt16(i + 14, true), z: v.getInt16(i + 16, true), valid: validity === 1 });
  }
  return result;
}
