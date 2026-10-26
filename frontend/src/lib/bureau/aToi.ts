import type { StreamState } from "../../hooks/streamState";
import { enEtapeSilencieuse, santeAgent } from "../santeAgent";

/** Un projet vu par la colonne : son nom, son run vivant si on le connaît, son état. */
export interface ProjetPourLaColonne {
  nom: string;
  etat: StreamState;
  runId?: string | null;
}

export interface QuestionAToi {
  projet: string;
  /** Sans run connu, la question s'affiche mais on ne peut pas y répondre d'ici. */
  runId: string | null;
  question: string;
  expireA: string | null;
}

export interface PrARelire {
  projet: string;
  pr: number;
}

export interface ContenuAToi {
  questions: QuestionAToi[];
  figes: string[];
  prs: PrARelire[];
}

/**
 * La PR d'un conflit résolu (ADR-033) : le dernier `livraison_done` porte des
 * `conflits`, un numéro de PR et un `arret`. Elle ne se merge jamais seule, un
 * humain la relit. Un `arret` absent ou vide dit une livraison ordinaire.
 */
export function prARelire(etat: StreamState): number | null {
  for (let i = etat.ticketEvents.length - 1; i >= 0; i--) {
    const ev = etat.ticketEvents[i];
    if (ev.type !== "livraison_done") continue;
    const conflits = ev.data["conflits"];
    const arret = ev.data["arret"];
    const pr = ev.data["pr_number"];
    const resolu = Array.isArray(conflits) && conflits.length > 0 && typeof arret === "string" && arret !== "";
    return resolu && typeof pr === "number" ? pr : null;
  }
  return null;
}

/**
 * Tout ce qui attend une action humaine : questions, agents figés, PR à relire.
 *
 * Un run clos n'est jamais « figé » : son dernier événement est vieux de
 * toujours (même règle que `contourDeLaPiece`).
 */
export function contenuAToi(projets: readonly ProjetPourLaColonne[], maintenant: number): ContenuAToi {
  const contenu: ContenuAToi = { questions: [], figes: [], prs: [] };
  for (const { nom, etat, runId = null } of projets) {
    if (etat.pendingQuestion) {
      contenu.questions.push({
        projet: nom,
        runId,
        question: etat.pendingQuestion,
        expireA: etat.questionExpireA,
      });
    }
    const sante = santeAgent(
      etat.dernierEvenementA,
      maintenant,
      etat.pendingQuestion,
      etat.attenteExterieure !== null,
      enEtapeSilencieuse(etat),
    );
    if (!etat.runClosed && sante === "blocage_suspecte") contenu.figes.push(nom);
    const pr = prARelire(etat);
    if (pr !== null) contenu.prs.push({ projet: nom, pr });
  }
  return contenu;
}
