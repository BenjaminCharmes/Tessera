import type { BreakdownLine } from "../../types/api";

/** Ce qu'on affiche quand il n'y a rien à compter : jamais « 0 $ ». */
export const ABSENT = "—";

/** Les rôles qui rendent un verdict sur un run (ticket-429). */
export const ROLES_A_VERDICT: readonly string[] = [
  "reviewer",
  "validateur",
  "securite",
];

export interface ChiffresDuRole {
  appels: string;
  cout: string;
}

/**
 * Les appels et le coût d'un rôle sur la période, tirés de `per_agent`.
 * Un rôle absent de la liste, ou sans appel, n'a rien à montrer.
 */
export function chiffresDuRole(
  lignes: readonly BreakdownLine[],
  role: string,
): ChiffresDuRole {
  const ligne = lignes.find((l) => l.key === role);
  if (!ligne || ligne.calls === 0) return { appels: ABSENT, cout: ABSENT };
  return { appels: String(ligne.calls), cout: `$${ligne.cost_usd.toFixed(2)}` };
}

/**
 * Une phrase sur ce que fait le rôle : sa description dans le registre, sinon
 * la première ligne de texte de son prompt (un titre Markdown n'en est pas une).
 */
export function phraseDuRole(
  description: string | null | undefined,
  prompt: string,
): string {
  const declaree = description?.trim();
  if (declaree) return declaree;
  const ligne = prompt
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l !== "" && !l.startsWith("#"));
  return ligne ?? "";
}
