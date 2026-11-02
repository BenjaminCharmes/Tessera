/**
 * Les captures qu'un run a prises — ticket-620.
 *
 * Elles vivent hors du dépôt (ADR-021) : l'endpoint de liste et le service
 * d'une image sont les seuls moyens de les voir. Le nom d'un fichier porte
 * l'écran, la largeur et le thème : `<écran>-<largeur>-<thème>.png`.
 */
import { BASE, request } from "./http";
const MOTIF = /^([a-z0-9-]+)-([0-9]{1,4})-(clair|sombre)\.png$/;

export type ThemeDeCapture = "clair" | "sombre";

export interface Capture {
  fichier: string;
  ecran: string;
  largeur: number;
  theme: ThemeDeCapture;
}

export interface EcranCapture {
  ecran: string;
  captures: Capture[];
}

/** Lit un nom de fichier ; `null` si ce n'est pas celui d'une capture. */
export function lireUneCapture(fichier: string): Capture | null {
  const m = MOTIF.exec(fichier);
  if (m === null) return null;
  return { fichier, ecran: m[1], largeur: Number(m[2]), theme: m[3] as ThemeDeCapture };
}

/** Groupe par écran, dans l'ordre d'arrivée ; une largeur croissante, clair avant sombre. */
export function grouperParEcran(fichiers: readonly string[]): EcranCapture[] {
  const groupes = new Map<string, Capture[]>();
  for (const fichier of fichiers) {
    const capture = lireUneCapture(fichier);
    if (capture === null) continue;
    groupes.set(capture.ecran, [...(groupes.get(capture.ecran) ?? []), capture]);
  }
  return Array.from(groupes, ([ecran, captures]) => ({
    ecran,
    captures: [...captures].sort(
      (a, b) => a.largeur - b.largeur || a.theme.localeCompare(b.theme),
    ),
  }));
}

/** L'adresse d'une image du run, pour un `<img src>`. */
export function urlDeCapture(projectId: string, ticketId: string, fichier: string): string {
  const projet = encodeURIComponent(projectId);
  return `${BASE}/projects/${projet}/captures/${encodeURIComponent(fichier)}?ticket=${encodeURIComponent(ticketId)}`;
}

/** Les noms des images prises pour ce ticket ; liste vide si le run n'a rien capturé. */
export async function listerLesCaptures(projectId: string, ticketId: string): Promise<string[]> {
  const chemin = `/projects/${encodeURIComponent(projectId)}/captures?ticket=${encodeURIComponent(ticketId)}`;
  const corps = await request<{ captures: string[] }>(chemin);
  return corps.captures;
}
