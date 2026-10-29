import { revueDeLEvenement, verdictDuReviewer } from "../../components/FilDuRun/verdict";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import { estTourDePlan } from "./plan";
import type { EtatPoste, PosteId } from "./postesDuRun";

/**
 * Ce que l'écran d'un poste montre : une scène pour l'étape occupée, ✓ ou ✗ pour
 * l'étape faite. `allume` et `eteint` sont le pixel d'avant les scènes : un
 * codeur dont on ne sait pas ce qu'il fait, un poste libre.
 */
export type EcranId =
  | "code"
  | "lecture"
  | "tests"
  | "audit"
  | "diff"
  | "criteres"
  | "ok"
  | "ko"
  | "allume"
  | "eteint";

const OUTILS_D_ECRITURE: readonly string[] = ["Edit", "Write", "MultiEdit", "NotebookEdit"];
const OUTILS_DE_LECTURE: readonly string[] = ["Read", "Grep", "Glob", "NotebookRead"];

/** La scène d'un poste occupé. Le codeur dépend de son dernier outil ; les autres de leur étape. */
const SCENE_DE_L_ETAPE: Record<Exclude<PosteId, "codeur">, EcranId> = {
  testeur: "tests",
  securite: "audit",
  reviewer: "diff",
  validateur: "criteres",
};

function sceneDuCodeur(etat: StreamState): EcranId {
  const dernier = etat.dernierOutil;
  // Un outil du reviewer ne dit rien du codeur : seul le sien compte.
  if (dernier === null || (dernier.agent !== "codeur" && dernier.agent !== "architect")) return "allume";
  if (OUTILS_D_ECRITURE.includes(dernier.outil)) return "code";
  if (OUTILS_DE_LECTURE.includes(dernier.outil)) return "lecture";
  return "allume";
}

/** Vrai si l'événement referme l'étape du poste ; le tour de plan ne referme pas celle du codeur. */
function referme(ev: OrchestratorEvent, poste: PosteId): boolean {
  switch (poste) {
    case "codeur":
      return ev.type === "agent_done" && (ev.agent === "codeur" || ev.agent === "architect") && !estTourDePlan(ev);
    case "testeur":
      return ev.type === "test_result";
    case "securite":
      return ev.type === "security_audit_done";
    case "reviewer":
      return ev.type === "agent_done" && ev.agent === "reviewer";
    case "validateur":
      return ev.type === "validation_done";
  }
}

/** Le verdict d'une validation : `approved` quand il est là, sinon `verdict` ; illisible, il refuse. */
function validationApprouvee(ev: OrchestratorEvent): boolean {
  const approuve = ev.data["approved"];
  return typeof approuve === "boolean" ? approuve : ev.data["verdict"] === "APPROVED";
}

/**
 * Le verdict favorable d'un événement de fin. Le codeur n'en rend aucun : avoir fini
 * vaut ✓. Les autres portes échouent fermées : sans verdict lisible, c'est ✗.
 */
function favorable(ev: OrchestratorEvent, poste: PosteId): boolean {
  switch (poste) {
    case "codeur":
      return true;
    case "testeur":
      return ev.data["passed"] === true;
    case "securite":
      return ev.data["verdict"] === "PASS";
    case "reviewer":
      return verdictDuReviewer(revueDeLEvenement(ev)) === "APPROVED";
    case "validateur":
      return validationApprouvee(ev);
  }
}

function sceneFaite(etat: StreamState, poste: PosteId): EcranId {
  const fin = etat.ticketEvents.findLast((ev) => referme(ev, poste));
  return fin === undefined || favorable(fin, poste) ? "ok" : "ko";
}

/**
 * L'écran du poste, lu dans les événements du run : la scène de son étape quand il
 * est occupé, le dernier verdict de son étape quand il a fini, rien quand il est libre.
 */
export function ecranDuPoste(etat: StreamState, poste: PosteId, etatPoste: EtatPoste): EcranId {
  if (etatPoste === "libre") return "eteint";
  if (etatPoste === "fait") return sceneFaite(etat, poste);
  return poste === "codeur" ? sceneDuCodeur(etat) : SCENE_DE_L_ETAPE[poste];
}
