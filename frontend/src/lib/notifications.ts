import type { RunActif } from "../types/api";
import type { StreamState } from "../hooks/streamState";
import type { SanteAgent } from "./santeAgent";

/**
 * Ce qui mérite de sortir de l'IDE — ticket-192.
 *
 * Une question d'agent, un run bloqué, un run terminé. Pas chaque ticket
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
  /** Santé de chaque run en cours (ticket-553). Absente : aucun run n'est suspecté. */
  sante?: Record<string, SanteAgent>;
}

function nom(run: RunActif): string {
  return run.ticket_id ? `${run.project_id} · ${run.ticket_id}` : run.project_id;
}

/** Une seule notification par passage : tant que l'agent reste « figé ? », rien de plus. */
function devientFige(runId: string, avant: Instantane, apres: Instantane): boolean {
  return (
    apres.sante?.[runId] === "blocage_suspecte" && avant.sante?.[runId] !== "blocage_suspecte"
  );
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
    if (devientFige(run.run_id, avant, apres)) {
      notifs.push({
        projectId: run.project_id,
        titre: `${nom(run)} : un agent semble figé`,
        corps: `${etat.currentAgent ?? "L'agent"} n'a rien émis depuis plus de 3 minutes.`,
      });
    }
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
