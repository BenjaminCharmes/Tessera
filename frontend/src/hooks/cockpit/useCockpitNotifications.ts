import { useRituels } from "../useRituels";
import { useNotificationsSysteme } from "../useNotificationsSysteme";
import type { CockpitActions } from "./useCockpitActions";
import type { CockpitNoyau } from "./useCockpitNoyau";

/**
 * Région des notifications — ticket-696 : le rail de navigation (pastilles,
 * cloche, réglage) et la case « Son » que le Bureau reprend.
 */
export function useCockpitNotifications(n: CockpitNoyau, a: CockpitActions) {
  const { supervision, runsStatus, appsEnCours, project } = n;
  const notifications = useNotificationsSysteme(
    supervision,
    project?.id ?? null,
    a.ouvrirProjet,
  );

  const rituels = useRituels();

  // Ce que la pastille doit dire avant tout le reste : un agent qui attend
  // bloque un humain, un run bloqué demande une décision. L'activité est le
  // cas nominal, donc le dernier à mériter la couleur.
  // Lire depuis runsStatus (store) : ne change pas à chaque token (ticket-354).
  const alerteDeSupervision = runsStatus.some((e) => e.status === "error")
    ? ("bloque" as const)
    : runsStatus.some((e) => e.pendingQuestion !== null)
      ? ("attente" as const)
      : null;

  return {
    rituels,
    navRail: {
      runsActifs: supervision.runs.length,
      appsEnCours: appsEnCours.apps?.length ?? 0,
      rituelsEnRetard: rituels.enRetard,
      alerte: alerteDeSupervision,
      notifications: { active: notifications.active, etat: notifications.etat, onChange: notifications.setActive },
      cloche: notifications.cloche,
    },
    // Le Bureau n'a pas de réglage à lui : c'est la case « Son » de la question (ticket-554).
    son: {
      actif: notifications.cloche.reglages.question.son,
      regler: (v: boolean) => notifications.cloche.setReglage("question", "son", v),
    },
  };
}
