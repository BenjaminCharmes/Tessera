import type { PipelineRun } from "../../types/api";
import type { VentilationDuProjet } from "../ventilation";
import type { LigneDeLAgent } from "./agentChoisi";
import { firstTryCount, weekRunCount } from "./weekEmployee";

/**
 * La ligne des runs : ceux de la semaine sur le projet, dont ceux approuvés au
 * premier tour (`firstTryCount`). Sans lecture, ou sans run sur la semaine, pas
 * de ligne : un « 0 » dirait ce qu'on ne sait pas (ADR-058).
 */
export function ligneDesRuns(
  runs: readonly PipelineRun[] | null,
  maintenant: number,
): LigneDeLAgent | null {
  if (runs === null) return null;
  const total = weekRunCount(runs, maintenant);
  if (total === 0) return null;
  const premierCoup = firstTryCount(runs, maintenant);
  return {
    libelle: "Runs de la semaine",
    valeur: `${total}, dont ${premierCoup} approuvé${premierCoup > 1 ? "s" : ""} au premier tour`,
  };
}

/**
 * La ligne du coût : ce que le rôle a dépensé sur le projet depuis toujours, lu
 * dans la ventilation par rôle. Sans lecture, ou sans appel de ce rôle : pas de ligne.
 */
export function ligneDuCout(
  ventilation: VentilationDuProjet | null,
  role: string,
): LigneDeLAgent | null {
  const depense = ventilation?.per_agent.find((d) => d.role === role);
  if (!depense) return null;
  return { libelle: "Coût cumulé", valeur: `${depense.total_cost_usd.toFixed(2).replace(".", ",")} $` };
}

/** Les lignes du bilan, dans l'ordre du panneau ; une lecture absente retire la sienne seule. */
export function lignesDuBilan(
  runs: readonly PipelineRun[] | null,
  ventilation: VentilationDuProjet | null,
  role: string,
  maintenant: number,
): LigneDeLAgent[] {
  return [ligneDesRuns(runs, maintenant), ligneDuCout(ventilation, role)].filter(
    (l): l is LigneDeLAgent => l !== null,
  );
}
