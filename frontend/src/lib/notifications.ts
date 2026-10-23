import type { RunActif } from "../types/api";
import type { StreamState } from "../hooks/streamState";

/**
 * Ce qui mérite de sortir de l'IDE — ticket-192.
 *
 * Une question d'agent, un run bloqué, un run terminé, l'issue de la
 * livraison (PR mergée ou non, ticket-552). Pas chaque ticket
 * approuvé d'une file : le bruit tuerait le signal. Pure, pour être testée
 * sans fenêtre : le hook lui donne l'avant et l'après, elle dit quoi dire.
 */
export interface Notif {
  projectId: string;
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
}

function nom(run: RunActif): string {
  return run.ticket_id ? `${run.project_id} · ${run.ticket_id}` : run.project_id;
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
      titre: `${nom(run)} : PR mergée`,
      corps: pr ? `La PR #${pr} est mergée.` : "La PR est mergée.",
    };
  }
  return {
    projectId: run.project_id,
    titre: `${nom(run)} : PR non mergée`,
    corps: etat.ciMerge.arret ?? "La PR reste ouverte, sans raison donnée.",
  };
}

export function notificationsPour(avant: Instantane, apres: Instantane, vue: Vue): Notif[] {
  const notifs: Notif[] = [];

  for (const run of apres.runs) {
    const etat = apres.etats[run.run_id];
    const precedent = avant.etats[run.run_id];
    if (!etat) continue;
    if (etat.pendingQuestion && etat.pendingQuestion !== precedent?.pendingQuestion) {
      notifs.push({
        projectId: run.project_id,
        titre: `${nom(run)} : un agent pose une question`,
        corps: etat.pendingQuestion,
      });
    }
    if (etat.status === "error" && precedent?.status !== "error") {
      notifs.push({
        projectId: run.project_id,
        titre: `${nom(run)} : run bloqué`,
        corps: etat.errorMessage ?? "Le run s'est arrêté sans approbation.",
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
    notifs.push({ projectId: run.project_id, titre: `${nom(run)} : terminé`, corps });
  }

  // Le toast suffit quand on regarde déjà ce projet.
  return notifs.filter((n) => !(vue.visible && n.projectId === vue.projetActif));
}
