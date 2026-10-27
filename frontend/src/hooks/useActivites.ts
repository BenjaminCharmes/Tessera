import { useState } from "react";
import { appliquerPlafond, renouveler } from "../lib/bureau/activites";
import type { Activites, Hasard } from "../lib/bureau/activites";
import { POSTES } from "../lib/bureau/postesDuRun";
import type { PosteId } from "../lib/bureau/postesDuRun";

interface Releve {
  /** Les postes finis et l'instant de l'horloge à la dernière mise à jour. */
  cle: string;
  instant: number;
  brutes: Activites;
}

/**
 * Les activités des agents qui ont fini, renouvelées à chaque tour de l'horloge
 * du Bureau (`maintenant`) : la pièce n'ouvre aucun minuteur. Un agent qui vient
 * de finir reçoit la sienne dans le même rendu.
 *
 * Le tirage se fait en ajustant l'état pendant le rendu, pas dans un effet : le
 * nouvel état est écrit avant que React ne peigne, sans second passage visible.
 */
export function useActivites(
  faits: readonly PosteId[],
  maintenant: number,
  hasard: Hasard = Math.random,
): Activites {
  const cle = POSTES.filter((p) => faits.includes(p)).join(",");
  const [releve, setReleve] = useState<Releve>({ cle: "", instant: Number.NaN, brutes: {} });
  if (releve.cle !== cle || releve.instant !== maintenant) {
    setReleve({ cle, instant: maintenant, brutes: renouveler(releve.brutes, faits, hasard) });
  }
  return appliquerPlafond(releve.brutes, faits);
}
