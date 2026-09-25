/**
 * Origine du backend, figée au build.
 *
 * Vide en dev : les URL restent relatives et le proxy Vite les résout. En
 * release Tauri la page est servie depuis `tauri://localhost`, où rien ne
 * répond sur `/api/v1` — `.env.production` pose alors `VITE_API_URL` et
 * chaque appel REST, WebSocket ou fichier part vers cette origine.
 *
 * Le slash final est retiré pour que `${API_ORIGIN}/api/v1/...` ne produise
 * jamais de double slash.
 */
const brut: string = import.meta.env.VITE_API_URL ?? "";

export const API_ORIGIN: string = brut.replace(/\/+$/, "");
