import { useCockpitNoyau } from "./cockpit/useCockpitNoyau";
import { useCockpitActions } from "./cockpit/useCockpitActions";
import { useCockpitNotifications } from "./cockpit/useCockpitNotifications";
import { useCockpitAgent } from "./cockpit/useCockpitAgent";
import { useCockpitSidebar } from "./cockpit/useCockpitSidebar";
import { useCockpitCentre } from "./cockpit/useCockpitCentre";
import { useCockpitBottomPanel } from "./cockpit/useCockpitBottomPanel";

export {
  panelAfterProjectSwitch,
  porteeEffectiveFor,
  runCachePour,
  prochainEtatKanban,
  eventsAffichiesFor,
} from "./cockpit/regles";

/**
 * The cockpit's state graph — ticket-252, split by region in ticket-696.
 *
 * App.tsx portait tout : l'état, les hooks, les gestionnaires, et une
 * cinquantaine de props passées à plat vers la colonne latérale. Ce hook
 * appelle un hook par région (`hooks/cockpit/`) et rend des groupes prêts à
 * poser sur chaque région — App ne fait plus que composer la grille.
 *
 * ADR-013 tient toujours : pas de store. Si les groupes ne suffisent plus,
 * la réévaluation (Zustand) mérite son propre ADR, pas un glissement.
 */
export function useCockpit() {
  const noyau = useCockpitNoyau();
  const actions = useCockpitActions(noyau);
  const { navRail, son, rituels } = useCockpitNotifications(noyau, actions);
  const agent = useCockpitAgent(noyau);

  return {
    panel: noyau.panel,
    setPanel: noyau.setPanel,
    ouvrirTicket: actions.ouvrirTicket,
    navRail,
    sidebar: useCockpitSidebar(noyau, actions, agent),
    centre: { ...useCockpitCentre(noyau, actions, agent, son), rituels },
    bottomPanel: useCockpitBottomPanel(noyau),
    toasts: noyau.toasts,
    fermerToast: noyau.removeToast,
  };
}
