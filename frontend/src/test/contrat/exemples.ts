import type { QuotaWindows } from "../../lib/quota";
import type { StatutDuRun } from "../../lib/statutDuRun";
import type { VentilationDuProjet } from "../../lib/ventilation";
import type { PlanDeNettoyage, ServiceActif } from "../../types/api";
import { CONFRONTATIONS, schemaVise, type Confrontation } from "./champs";
import { valider, exempleDe } from "./valider";

/**
 * Les fixtures des routes du périmètre : l'exemple vient du schéma du backend,
 * le test ne change que ce qui l'intéresse. Un champ inventé ou une valeur du
 * mauvais type fait lever la fabrique, avant même que le composant la lise.
 */
function fabriquer<T extends object>(libelle: string, surcharges: Partial<T>): T {
  const c: Confrontation | undefined = CONFRONTATIONS.find((x) => x.libelle === libelle);
  if (c === undefined) throw new Error(`Aucune confrontation « ${libelle} »`);
  const schema = schemaVise(c);
  const valeur = { ...(exempleDe(schema) as T), ...surcharges };
  const ecarts = valider(schema, valeur);
  if (ecarts.length > 0) throw new Error(`Fixture « ${libelle} » non conforme :\n  - ${ecarts.join("\n  - ")}`);
  return valeur;
}

/** Une réponse de `GET /runs/{id}` : aucun ticket, un seul tableau vide à la fois. */
export function statutDuRun(surcharges: Partial<StatutDuRun> = {}): StatutDuRun {
  return fabriquer<StatutDuRun>("StatutDuRun", { ticket_courant: null, fin: null, approuves: [], arretes: [], restants: [], ...surcharges });
}

/** Une réponse de `GET /projects/{id}/usage/breakdown`, sans dépense par défaut. */
export function ventilation(surcharges: Partial<VentilationDuProjet> = {}): VentilationDuProjet {
  return fabriquer<VentilationDuProjet>("VentilationDuProjet", { per_agent: [], per_model: [], per_project: [], ...surcharges });
}

/** Une réponse de `GET /usage/quota`, sans fenêtre connue par défaut. */
export function fenetresDeQuota(surcharges: Partial<QuotaWindows> = {}): QuotaWindows {
  return fabriquer<QuotaWindows>("QuotaWindows", { windows: {}, ...surcharges });
}

/** Un élément de `GET /projects/{id}/services` : un service arrêté, rien en sortie. */
export function serviceActif(surcharges: Partial<ServiceActif> = {}): ServiceActif {
  return fabriquer<ServiceActif>("ServiceActif (liste)", { pid: null, code_de_sortie: null, sortie: [], ...surcharges });
}

/** Une réponse de `GET /projects/{id}/branches/cleanup`, sans branche par défaut. */
export function planDeNettoyage(surcharges: Partial<PlanDeNettoyage> = {}): PlanDeNettoyage {
  return fabriquer<PlanDeNettoyage>("PlanDeNettoyage", { nettoyables: [], conservees: [], ...surcharges });
}
