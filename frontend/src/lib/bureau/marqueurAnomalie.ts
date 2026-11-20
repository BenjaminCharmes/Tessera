import type { PosteId } from "./postesDuRun";
import type { RunActif } from "../../types/api";

/** Le nom accessible du marqueur : « 1 anomalie », « 3 anomalies ». */
export function libelleDesAnomalies(nombre: number): string {
  return `${nombre} ${nombre > 1 ? "anomalies" : "anomalie"}`;
}

/**
 * Le poste qui porte le marqueur d'anomalie du run, ou `null` (ADR-078, ADR-058).
 *
 * Une donnée ou rien : sans anomalie dans l'instantané, ou run clos, aucun marqueur ; sans
 * agent au travail, personne à marquer — le Bureau ne dessine pas d'agent pour l'occasion.
 * Un seul poste, le premier à travailler, quel que soit le nombre d'anomalies.
 */
export function posteDuMarqueur(
  run: RunActif | undefined,
  clos: boolean,
  postesAuTravail: readonly PosteId[],
): { poste: PosteId; nombre: number } | null {
  const nombre = run?.anomalies?.length ?? 0;
  const poste = postesAuTravail[0];
  return clos || nombre === 0 || poste === undefined ? null : { poste, nombre };
}
