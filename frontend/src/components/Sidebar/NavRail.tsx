import type { ReactElement } from "react";
import type { AlerteDeSupervision, SidebarPanel } from "./panels";
import Pastille from "./Pastille";
import { BAND } from "../../design/layout";
import {
  IconChart,
  IconChat,
  IconFolder,
  IconHistory,
  IconLayers,
  IconList,
  IconRadar,
  IconRobot,
} from "../../design/icons";

/**
 * Barre de navigation principale du cockpit (ticket-065).
 *
 * Elle remplace une barre de cinq glyphes empruntés à cinq familles
 * différentes — dont le sens n'apparaissait qu'au survol. Deux décisions en
 * découlent :
 *
 * - **un seul jeu d'icônes**, celui de `design/icons.tsx` (ticket-251 les y a
 *   ramenées : elles étaient tracées ici sur une grille locale identique) ;
 * - **un libellé visible** sous chaque icône. Une infobulle se mérite au
 *   survol ; un libellé se lit tout de suite.
 */
interface NavRailProps {
  activePanel: SidebarPanel;
  onChangePanel: (panel: SidebarPanel) => void;
  /**
   * Combien de **runs** tournent, tous projets confondus — pas combien
   * d'agents (ticket-129). Un pipeline Tessera est séquentiel : il n'y a
   * jamais deux agents simultanés dans un même run, et annoncer « 12 agents »
   * serait faux.
   */
  runsActifs?: number;
  /** Ce qui mérite d'être vu avant le reste, quand c'est le cas. */
  alerte?: AlerteDeSupervision;
}

interface Destination {
  panel: SidebarPanel;
  label: string;
  icon: ReactElement;
}

const DESTINATIONS: Destination[] = [
  { panel: "projects", label: "Projets", icon: <IconLayers size={20} /> },
  { panel: "tickets", label: "Tickets", icon: <IconList size={20} /> },
  { panel: "files", label: "Fichiers", icon: <IconFolder size={20} /> },
  { panel: "history", label: "Historique", icon: <IconHistory size={20} /> },
  { panel: "agents", label: "Agents", icon: <IconRobot size={20} /> },
  {
    panel: "supervision",
    label: "Supervision",
    icon: <IconRadar size={20} />,
  },
  { panel: "usage", label: "Statistiques", icon: <IconChart size={20} /> },
  { panel: "chat", label: "Chat", icon: <IconChat size={20} /> },
];

export default function NavRail({
  activePanel,
  onChangePanel,
  runsActifs = 0,
  alerte = null,
}: NavRailProps) {
  return (
    <nav
      role="tablist"
      aria-orientation="vertical"
      aria-label="Navigation principale"
      className="flex h-full flex-col items-stretch gap-0.5 bg-zinc-900 px-1.5 pb-3 pt-2"
    >
      {/*
        Zone d'identité — ticket-101.
        ADR-026 : l'accent d'identité est une barre, jamais la couleur d'un
        mot. Le violet porte la marque (SVG), le nom se rend en neutre (zinc).
      */}
      <div
        className={`${BAND} mb-1 flex-col justify-center gap-0.5 border-b border-zinc-800`}
      >
        {/*
          La marque vient du favicon plutôt que d'un SVG recopié ici : deux
          dessins d'une même marque finissent toujours par diverger, et c'est
          celui qu'on ne regarde pas qui dérive.
        */}
        <img src="/favicon.svg" width={18} height={18} alt="" aria-hidden />
        <span className="text-micro leading-none text-zinc-400">Tessera</span>
      </div>
      {DESTINATIONS.map(({ panel, label, icon }) => {
        const actif = activePanel === panel;
        return (
          <button
            key={panel}
            type="button"
            role="tab"
            aria-selected={actif}
            onClick={() => onChangePanel(panel)}
            className={`relative flex flex-col items-center gap-1 rounded-md px-1 py-2 transition-colors ${
              actif
                ? "bg-violet-500/15 text-zinc-100 ring-1 ring-inset ring-violet-500/40"
                : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-200"
            }`}
          >
            {panel === "supervision" ? (
              <Pastille nombre={runsActifs} alerte={alerte} />
            ) : null}
            {icon}
            <span className="w-full text-center text-micro leading-none">
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
