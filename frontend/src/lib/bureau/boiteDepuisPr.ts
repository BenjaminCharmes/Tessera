import type { PRStatus } from "../../types/api";
import type { BoiteAuxLettres } from "./boiteAuxLettres";

/**
 * L'état de la boîte relu depuis l'état d'une PR (`pr-statuses`), quand les
 * événements du run ne sont plus là — après un rechargement de page.
 *
 * `open` avec une CI `pending` : le watcher attend la CI. Toute autre PR ouverte
 * est laissée à un humain. `closed` n'a pas été mergée : `refusee`.
 */
export function boiteDepuisPr(pr: PRStatus | null | undefined): BoiteAuxLettres {
  if (!pr) return { etat: "aucune", pr: null };
  const numero = pr.pr_number;
  if (pr.state === "merged") return { etat: "mergee", pr: numero };
  if (pr.state === "closed") return { etat: "refusee", pr: numero };
  return { etat: pr.ci_status === "pending" ? "ci" : "ouverte", pr: numero };
}
