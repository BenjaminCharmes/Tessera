import type { StreamState } from "../../hooks/streamState";
import type { EtatPastille } from "../../design/ui/StatusPill";
import type { IssueDuRun } from "./issueDuRun";

/** Ce que la pastille d'un run dit de son état, dans la Liste comme dans le Bureau. */
export interface EtatAffiche {
  etat: EtatPastille;
  libelle: string;
}

/** L'état d'un run en un mot : bloqué, en attente d'une réponse, ou l'agent au travail. */
export function etatAffiche(etat: StreamState): EtatAffiche {
  if (etat.status === "error") return { etat: "echec", libelle: "bloqué" };
  if (etat.pendingQuestion !== null) return { etat: "attention", libelle: "attend une réponse" };
  return { etat: "en-cours", libelle: etat.currentAgent ?? "en cours" };
}

const ISSUES: Record<Exclude<IssueDuRun, "en-cours">, EtatAffiche> = {
  termine: { etat: "reussi", libelle: "terminé" },
  bloque: { etat: "echec", libelle: "bloqué" },
  erreur: { etat: "echec", libelle: "en erreur" },
  autre: { etat: "neutre", libelle: "clos" },
};

/** Le mot d'une issue, ou `null` tant que le run court. */
export function issueAffichee(issue: IssueDuRun): EtatAffiche | null {
  return issue === "en-cours" ? null : ISSUES[issue];
}

/** L'instant de clôture d'un run (événement `run_closed`), `undefined` tant qu'il court. */
export function clotureDuRun(etat: StreamState): string | undefined {
  return etat.events.find((e) => e.type === "run_closed")?.timestamp;
}
