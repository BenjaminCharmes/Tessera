import type { BoiteAuxLettres } from "./boiteAuxLettres";

const LIBELLE_ETAT = {
  ouverte: "ouverte",
  ci: "CI en attente",
  mergee: "mergée",
  refusee: "refusée",
} as const;

const PREFIXE = "Boîte aux lettres, ";

/** L'état de la boîte sans son préfixe : « aucune PR », « PR #12 ouverte ». */
export function libelleCourtDeLaBoite({ etat, pr }: BoiteAuxLettres): string {
  if (etat === "aucune") return "aucune PR";
  const numero = pr === null ? "PR" : `PR #${pr}`;
  return `${numero} ${LIBELLE_ETAT[etat]}`;
}

/** Ce que dit la boîte aux lettres, en mots : un `aria-label` distinct par état. */
export function libelleDeLaBoite(boite: BoiteAuxLettres): string {
  return `${PREFIXE}${libelleCourtDeLaBoite(boite)}`;
}
