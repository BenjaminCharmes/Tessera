export type VueCentre = "run" | "diff" | "kanban" | "editor";

interface Etat {
  /** Un run tourne — `stream.status` vaut `running` ou `connecting`. */
  runEnCours: boolean;
  /** L'utilisateur n'a rien demandé d'autre depuis que le run a démarré. */
  runAuPremierPlan: boolean;
  openFilePath: string | null;
  showDiff: boolean;
  showKanban: boolean;
}

/**
 * Ce que montre le centre — ticket-178.
 *
 * C'était une cascade de priorités où `RunView` était testé en premier :
 * « Vue liste » et « Vue tableau » n'avaient plus aucun effet tant qu'un run
 * tournait, et rien ne l'expliquait. La cascade traitait `openFilePath` et
 * `showDiff` comme des choix de l'utilisateur, mais la vue du run comme un état
 * dérivé de `stream.status` — alors que c'est une vue parmi les autres.
 *
 * Un choix qui ne peut pas s'exprimer n'est pas un choix : le run passe devant
 * quand il démarre, tout geste explicite le lui reprend.
 */
export function vueDuCentre({
  runEnCours,
  runAuPremierPlan,
  openFilePath,
  showDiff,
  showKanban,
}: Etat): VueCentre {
  if (openFilePath) return "editor";
  if (showDiff) return "diff";
  if (runEnCours && runAuPremierPlan) return "run";
  return showKanban ? "kanban" : "editor";
}
