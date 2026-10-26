import Sidebar from "./components/Sidebar";
import NavRail from "./components/Sidebar/NavRail";
import CenterView from "./components/CenterView";
import BottomPanel from "./components/BottomPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import ToastContainer from "./components/Toast";
import {
  GRILLE_COCKPIT,
  GRILLE_COCKPIT_SANS_COLONNE,
  PANNEAUX_SANS_COLONNE,
} from "./design/layout";
import { useCockpit } from "./hooks/useCockpit";
import { OuvrirTicketContext } from "./hooks/useOuvrirTicket";

/**
 * La composition du cockpit — rien d'autre (ticket-252).
 *
 * L'état, les gestionnaires et le câblage entre régions vivent dans
 * `useCockpit` ; le choix de la vue centrale dans `CenterView`. Ce fichier ne
 * dit plus qu'une chose : où chaque région se pose dans la grille.
 */
export default function App() {
  const cockpit = useCockpit();
  // Sans contenu pour le panneau actif, la colonne n'est pas rendue (ticket-580).
  const avecColonne = !PANNEAUX_SANS_COLONNE.includes(cockpit.panel);
  const colonneCentre = avecColonne ? "3" : "2";

  return (
    <OuvrirTicketContext.Provider value={cockpit.ouvrirTicket}>
    <div
      className="h-screen overflow-hidden bg-zinc-900 text-zinc-100"
      style={avecColonne ? GRILLE_COCKPIT : GRILLE_COCKPIT_SANS_COLONNE}
    >
      {/* Rail de navigation — col. 1, lignes 1-2 */}
      <div
        className="border-r border-zinc-700"
        style={{ gridColumn: "1", gridRow: "1 / 3" }}
      >
        <NavRail
          activePanel={cockpit.panel}
          onChangePanel={cockpit.setPanel}
          runsActifs={cockpit.navRail.runsActifs}
          appsEnCours={cockpit.navRail.appsEnCours}
          alerte={cockpit.navRail.alerte}
          notifications={cockpit.navRail.notifications}
          cloche={cockpit.navRail.cloche}
        />
      </div>

      {/* Colonne latérale — col. 2, lignes 1-2.
          Nommée : depuis que le tableau des tickets occupe le centre, les
          mêmes titres apparaissent des deux côtés. Une assertion qui ne dit
          pas de quelle région elle parle en trouve deux. */}
      {avecColonne ? (
        <aside
          aria-label="Panneau latéral"
          className="border-r border-zinc-700 overflow-hidden"
          style={{ gridColumn: "2", gridRow: "1 / 3" }}
        >
          <ErrorBoundary>
            <Sidebar panel={cockpit.panel} {...cockpit.sidebar} />
          </ErrorBoundary>
        </aside>
      ) : null}

      {/* Centre — col. 3 (col. 2 sans colonne latérale), ligne 1 */}
      <main
        aria-label="Vue principale"
        className="overflow-hidden"
        style={{ gridColumn: colonneCentre, gridRow: "1" }}
      >
        <ErrorBoundary>
          <CenterView panel={cockpit.panel} {...cockpit.centre} />
        </ErrorBoundary>
      </main>

      {/* Bandeau des événements — col. 3, ligne 2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: colonneCentre, gridRow: "2" }}
      >
        <BottomPanel {...cockpit.bottomPanel} />
      </div>

      <ToastContainer toasts={cockpit.toasts} onDismiss={cockpit.fermerToast} />
    </div>
    </OuvrirTicketContext.Provider>
  );
}
