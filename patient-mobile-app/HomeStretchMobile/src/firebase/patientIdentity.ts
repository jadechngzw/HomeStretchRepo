import { auth } from './config';
export function patientIdentity() {
  const user = auth.currentUser;
  if (!user) throw new Error('Sign in before recording.');
  return { id: user.uid, name: user.displayName || user.email || 'Patient' };
}
