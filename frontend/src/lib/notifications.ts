import type { RunActif } from "../types/api";
import type { StreamState } from "../hooks/streamState";
import { enEtapeSilencieuse } from "./santeAgent";
import type { SanteAgent } from "./santeAgent";
import { notificationsQuota } from "./notifQuota";
import type { RelevesDeQuota } from "./notifQuota";

/**
 * Ce qui mérite de sortir de l'IDE — ticket-192.
 *
 * Une question d'agent, un run bloqué, un run terminé, l'issue de la
 * livraison (PR mergée ou non, ticket-552), un quota de session ou de semaine
 * sous 10 % (ticket-555). Pas chaque ticket
 * approuvé d'une file : le bruit tuerait le signal. Pure, pour être testée
 * sans fenêtre : le hook lui donne l'avant et l'après, elle dit quoi dire.
 *
 * Elle rend toutes les notifications, y compris celles du projet affiché : elle
 * produit, elle ne décide pas de l'envoi (ticket-554).
 */
export const TYPES_NOTIF = [
  "question",
  "fige",
  "bloque",
  "termine",
  "merge",
  "ci_rouge",
  "quota_bas",
] as const;

/** Le genre d'événement : c'est lui que les réglages de la cloche choisissent (ticket-554). */
export type TypeNotif = (typeof TYPES_NOTIF)[number];

export interface Notif {
  projectId: string;
  type: TypeNotif;
  titre: string;
  corps: string;
}

export interface Vue {
  /** Le projet affiché, et si la fenêtre est au premier plan. */
  projetActif: string | null;
  visible: boolean;
}

export interface Instantane {
  runs: RunActif[];
  etats: Record<string, StreamState>;
  /** Santé de chaque run en cours (ticket-553). Absente : aucun run n'est suspecté. */
  sante?: Record<string, SanteAgent>;
  /** Relevés de quota par fenêtre (ticket-555). Absent : pas encore lus. */
  quota?: RelevesDeQuota;
  /** L'instant de l'instantané, pour dire l'heure de reprise ; `Date.now()` à défaut. */
  maintenant?: number;
}

function nom(run: RunActif): string {
  return run.ticket_id ? `${run.project_id} · ${run.ticket_id}` : run.project_id;
}

/**
 * Une seule notification par passage : tant que l'agent reste « figé ? », rien de plus.
 * Pendant une étape silencieuse, le silence n'est pas un signe (ticket-587) : même
 * si la santé reçue dit « figé ? », rien ne part.
 */
function devientFige(runId: string, avant: Instantane, apres: Instantane): boolean {
  const etat = apres.etats[runId];
  if (etat && enEtapeSilencieuse(etat)) return false;
  return (
    apres.sante?.[runId] === "blocage_suspecte" && avant.sante?.[runId] !== "blocage_suspecte"
  );
}

// L'issue de la phase 2 de livraison (ADR-051) arrive après la fin du run, sous
// un seul événement `ci_merge_done` : mergée, ou non mergée avec sa raison
// (CI rouge, merge refusé, tête changée, délai) dans `arret`.
function notifLivraison(run: RunActif, etat: StreamState, precedent: StreamState | undefined): Notif | null {
  // Comparaison par référence : `ci_merge_done` crée un objet à chaque événement,
  // et `ciMerge` n'est jamais remis à null entre deux tickets d'une file.
  if (!etat.ciMerge || etat.ciMerge === precedent?.ciMerge) return null;
  if (etat.ciMerge.merged) {
    const pr = etat.livraisonPrNumber;
    return {
      projectId: run.project_id,
      type: "merge",
      titre: `${nom(run)} : PR mergée`,
      corps: pr ? `La PR #${pr} est mergée.` : "La PR est mergée.",
    };
  }
  return {
    projectId: run.project_id,
    type: "ci_rouge",
    titre: `${nom(run)} : PR non mergée`,
    corps: etat.ciMerge.arret ?? "La PR reste ouverte, sans raison donnée.",
  };
}

export function notificationsPour(avant: Instantane, apres: Instantane): Notif[] {
  const notifs: Notif[] = [];

  for (const run of apres.runs) {
    const etat = apres.etats[run.run_id];
    const precedent = avant.etats[run.run_id];
    if (!etat) continue;
    if (etat.pendingQuestion && etat.pendingQuestion !== precedent?.pendingQuestion) {
      notifs.push({
        projectId: run.project_id,
        type: "question",
        titre: `${nom(run)} : un agent pose une question`,
        corps: etat.pendingQuestion,
      });
    }
    if (etat.status === "error" && precedent?.status !== "error") {
      notifs.push({
        projectId: run.project_id,
        type: "bloque",
        titre: `${nom(run)} : run bloqué`,
        corps: etat.errorMessage ?? "Le run s'est arrêté sans approbation.",
      });
    }
    if (devientFige(run.run_id, avant, apres)) {
      notifs.push({
        projectId: run.project_id,
        type: "fige",
        titre: `${nom(run)} : un agent semble figé`,
        corps: `${etat.currentAgent ?? "L'agent"} n'a rien émis depuis plus de 3 minutes.`,
      });
    }
    const livraison = notifLivraison(run, etat, precedent);
    if (livraison) notifs.push(livraison);
  }

  const restants = new Set(apres.runs.map((r) => r.run_id));
  for (const run of avant.runs) {
    if (restants.has(run.run_id)) continue;
    const dernier = avant.etats[run.run_id];
    const resultat = dernier?.lastResult;
    const corps = resultat
      ? resultat.approved
        ? `${resultat.ticket_id} approuvé en ${resultat.rounds} tour${resultat.rounds > 1 ? "s" : ""}`
        : `${resultat.ticket_id} non approuvé`
      : run.mode === "queue"
        ? "La file est terminée."
        : "Le run est terminé.";
    notifs.push({ projectId: run.project_id, type: "termine", titre: `${nom(run)} : terminé`, corps });
  }

  notifs.push(...notificationsQuota(avant.quota, apres.quota, apres.maintenant ?? Date.now()));

  // Tout ce qui s'est produit : c'est l'historique de la cloche (ticket-554).
  // Ce qui part vers le système se filtre à part, par `masqueeParToast`.
  return notifs;
}

/** Le toast suffit quand on regarde déjà ce projet : rien ne part vers le système. */
export function masqueeParToast(n: Notif, vue: Vue): boolean {
  return vue.visible && n.projectId === vue.projetActif;
}
