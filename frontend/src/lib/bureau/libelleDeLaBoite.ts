import type { BoiteAuxLettres } from "./boiteAuxLettres";

const LIBELLE_ETAT = {
  ouverte: "ouverte",
  ci: "CI en attente",
  mergee: "mergée",
  refusee: "refusée",
} as const;

/** Ce que dit la boîte aux lettres, en mots : un `aria-label` distinct par état. */
export function libelleDeLaBoite({ etat, pr }: BoiteAuxLettres): string {
  if (etat === "aucune") return "Boîte aux lettres, aucune PR";
  const numero = pr === null ? "PR" : `PR #${pr}`;
  return `Boîte aux lettres, ${numero} ${LIBELLE_ETAT[etat]}`;
}
