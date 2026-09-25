import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { INITIAL } from "./streamState";
import type { StreamState, UseRunActifResult } from "./streamState";
import type { UseSupervisionResult } from "./useSupervision";
import type { RunRequest } from "../types/api";

/**
 * Le run du projet actif, vu depuis la supervision — ticket-129.
 *
 * `AgentPanel`, `RunView` et la sidebar veulent **un** run : celui du projet
 * qu'on regarde. La supervision les porte tous. Ce hook fait la projection,
 * et rend exactement l'interface que ces composants attendaient de
 * `useOrchestratorStream` — qui n'existe plus, faute de quoi deux sockets
 * auraient observé la même chose.
 *
 * Il ne détient aucun état de run : tout vient de `supervision`. Ce qu'il
 * garde en propre, c'est ce que la supervision ne peut pas savoir — quel run
 * *ce* projet vient de lancer, et si l'utilisateur a masqué le précédent.
 */
export function useRunActif(
  supervision: UseSupervisionResult,
  projectId: string | null,
): UseRunActifResult {
  const [lancement, setLancement] = useState<{
    enCours: boolean;
    erreur: string | null;
    ticketId: string | null;
  }>({ enCours: false, erreur: null, ticketId: null });
  // Le run masqué par `clear()` : la supervision le connaît encore, mais
  // cette vue-ci ne veut plus le montrer. C'est un **état** et non une ref :
  // il décide de ce qui s'affiche, et lire une ref pendant le rendu rend le
  // résultat dépendant du moment où React repasse.
  const [masque, setMasque] = useState<string | null>(null);

  const run =
    projectId === null
      ? undefined
      : supervision.runs.find(
          (r) => r.project_id === projectId && r.run_id !== masque,
        );

  const etat: StreamState = run ? supervision.etatDe(run.run_id) : INITIAL;

  // Déclarer le run qu'on affiche : ADR-041 ne pousse son texte qu'aux clients
  // abonnés, et seul un lancement ou un clic dans Supervision abonnait. Une
  // page rechargée montrait donc un agent figé (ticket-183).
  const { observerLeTexte } = supervision;
  const runId = run?.run_id ?? null;
  useEffect(() => {
    observerLeTexte(runId);
  }, [observerLeTexte, runId]);

  const lancer = useCallback(
    (corps: RunRequest, ticketId: string | null) => {
      if (!projectId) return;
      setMasque(null);
      setLancement({ enCours: true, erreur: null, ticketId });
      void demarrerUnRun(corps).then((reponse) => {
        if ("erreur" in reponse) {
          setLancement({ enCours: false, erreur: reponse.erreur, ticketId });
          return;
        }
        supervision.suivre({
          run_id: reponse.run_id,
          project_id: projectId,
          mode: corps.mode ?? "single",
          ticket_id: ticketId,
          etape: null,
          agent: null,
          tour: 0,
          tokens_entree: 0,
          tokens_sortie: 0,
          cout_usd: 0,
          verdict: null,
          demarre_a: new Date().toISOString(),
        });
        supervision.selectionner(reponse.run_id);
        setLancement({ enCours: false, erreur: null, ticketId });
      });
    },
    [projectId, supervision],
  );

  const envoyer = useCallback(
    (payload: Record<string, string>) => {
      if (run) supervision.envoyer(run.run_id, payload);
    },
    [run, supervision],
  );

  return {
    ...etat,
    // Un lancement en vol n'a pas encore de run : sans ce repli, le bouton
    // resterait « au repos » entre le clic et le premier événement.
    status: lancement.erreur
      ? "error"
      : lancement.enCours
        ? "connecting"
        : etat.status,
    errorMessage: lancement.erreur ?? etat.errorMessage,
    ticketId: etat.ticketId ?? lancement.ticketId,
    connect: (ticketId: string) =>
      lancer(
        { project_id: projectId ?? "", mode: "single", ticket_id: ticketId },
        ticketId,
      ),
    connectQueue: (ticketIds: string[]) => {
      if (ticketIds.length === 0) return;
      lancer(
        { project_id: projectId ?? "", mode: "queue", ticket_ids: ticketIds },
        ticketIds[0] ?? null,
      );
    },
    connectAutonome: (options: { depuisGithub: boolean }) =>
      lancer(
        {
          project_id: projectId ?? "",
          mode: "autonomous",
          depuis_github: options.depuisGithub,
        },
        null,
      ),
    disconnect: () => {
      // Ne ferme rien : la socket est partagée, et le run continue de toute
      // façon (ADR-041). On cesse seulement de l'afficher ici.
      setMasque(run?.run_id ?? null);
    },
    clear: () => {
      setMasque(run?.run_id ?? null);
      setLancement({ enCours: false, erreur: null, ticketId: null });
    },
    answer: (text: string) => envoyer({ type: "answer", text }),
    interject: (text: string) => envoyer({ type: "interject", text }),
    stop: () => envoyer({ type: "stop", text: "" }),
  };
}


/** Démarre un run et rend son identifiant, ou null si le lancement est refusé. */
export async function demarrerUnRun(
  corps: RunRequest,
): Promise<{ run_id: string } | { erreur: string }> {
  try {
    return await api.orchestrator.run(corps);
  } catch (erreur: unknown) {
    return {
      erreur: erreur instanceof Error ? erreur.message : "Lancement refusé",
    };
  }
}
