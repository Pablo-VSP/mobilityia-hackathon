/**
 * auth.ts — Firebase Authentication (reemplaza Amazon Cognito)
 *
 * Provee las mismas funciones que el auth.ts original:
 * - signIn(email, password)
 * - signOut()
 * - getIdToken()
 * - getCurrentUser()
 */

import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut as fbSignOut,
  onAuthStateChanged,
  type User,
} from 'firebase/auth';
import { config } from '../config';

// Initialize Firebase
const firebaseApp = initializeApp({
  apiKey: config.firebase.apiKey,
  authDomain: config.firebase.authDomain,
  projectId: config.firebase.projectId,
});

const auth = getAuth(firebaseApp);

export function getCurrentUser(): User | null {
  return auth.currentUser;
}

export async function getIdToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error('No user authenticated');
  return user.getIdToken();
}

export async function signIn(email: string, password: string): Promise<User> {
  const credential = await signInWithEmailAndPassword(auth, email, password);
  return credential.user;
}

export function signOut(): void {
  fbSignOut(auth);
}

/**
 * Subscribe to auth state changes.
 * Returns an unsubscribe function.
 */
export function onAuthChange(callback: (user: User | null) => void): () => void {
  return onAuthStateChanged(auth, callback);
}
