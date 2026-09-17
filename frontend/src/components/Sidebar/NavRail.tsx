import type { ReactElement } from "react";
import type { SidebarPanel } from "./panels";

/**
 * Barre de navigation principale du cockpit (ticket-065).
 *
 * Elle remplace une barre de cinq glyphes empruntés à cinq familles
 * différentes — `◈ ☰ ⏱ ⚙ $` — dont le sens n'apparaissait qu'au survol. Deux
 * décisions en découlent :
 *
 * - **un seul jeu d'icônes**, tracées ici en SVG sur la même grille de 24, au
 *   même trait, en `currentColor`. Aucune police d'icônes, aucun emoji : c'est
 *   ce qui rend la barre homogène quels que soient la plateforme et le thème ;
 * - **un libellé visible** sous chaque icône. Une infobulle se mérite au
 *   survol ; un libellé se lit tout de suite.
 */
interface NavRailProps {
  activePanel: SidebarPanel;
  onChangePanel: (panel: SidebarPanel) => void;
}

interface Destination {
  panel: SidebarPanel;
  label: string;
  icon: ReactElement;
}

// Toutes les icônes partagent viewBox, trait et jointures : c'est ce qui fait
// qu'elles se lisent comme une famille et non comme une collection.
const ICON = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  width: 20,
  height: 20,
  "aria-hidden": true,
};

const DESTINATIONS: Destination[] = [
  {
    panel: "projects",
    label: "Projets",
    icon: (
      <svg {...ICON}>
        <path d="M3 7.5 12 3l9 4.5-9 4.5z" />
        <path d="M3 12.5 12 17l9-4.5" />
        <path d="M3 17 12 21.5 21 17" />
      </svg>
    ),
  },
  {
    panel: "tickets",
    label: "Tickets",
    icon: (
      <svg {...ICON}>
        <path d="M8 6h12M8 12h12M8 18h12" />
        <path d="M4 6h.01M4 12h.01M4 18h.01" />
      </svg>
    ),
  },
  {
    panel: "files",
    label: "Fichiers",
    icon: (
      <svg {...ICON}>
        <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2.5h7A1.5 1.5 0 0 1 19 9v8.5A1.5 1.5 0 0 1 17.5 19h-13A1.5 1.5 0 0 1 3 17.5z" />
      </svg>
    ),
  },
  {
    panel: "history",
    label: "Historique",
    icon: (
      <svg {...ICON}>
        <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
        <path d="M3 4v4h4" />
        <path d="M12 7.5V12l3 1.8" />
      </svg>
    ),
  },
  {
    panel: "agents",
    label: "Agents",
    icon: (
      <svg {...ICON}>
        <rect x="4.5" y="7.5" width="15" height="12" rx="2.5" />
        <path d="M12 3.5v4" />
        <path d="M9 12.5h.01M15 12.5h.01" />
        <path d="M9.5 16h5" />
      </svg>
    ),
  },
  {
    panel: "usage",
    label: "Coûts",
    icon: (
      <svg {...ICON}>
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
      </svg>
    ),
  },
];

export default function NavRail({ activePanel, onChangePanel }: NavRailProps) {
  return (
    <nav
      role="tablist"
      aria-orientation="vertical"
      aria-label="Navigation principale"
      className="flex h-full flex-col items-stretch gap-0.5 bg-zinc-900 px-2 py-3"
    >
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
                ? "bg-zinc-800 text-violet-200"
                : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-200"
            }`}
          >
            {actif && (
              <span
                aria-hidden="true"
                className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-r-full bg-violet-400"
              />
            )}
            {icon}
            <span className="text-micro leading-none">
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
