import Sidebar from "./components/Sidebar";
import NavRail from "./components/Sidebar/NavRail";
import CenterView from "./components/CenterView";
import BottomPanel from "./components/BottomPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import ToastContainer from "./components/Toast";
import { GRILLE_COCKPIT } from "./design/layout";
import { useCockpit } from "./hooks/useCockpit";

/**
 * La composition du cockpit — rien d'autre (ticket-252).
 *
 * L'état, les gestionnaires et le câblage entre régions vivent dans
 * `useCockpit` ; le choix de la vue centrale dans `CenterView`. Ce fichier ne
 * dit plus qu'une chose : où chaque région se pose dans la grille.
 */
export default function App() {
  const cockpit = useCockpit();

  return (
    <div
      className="h-screen overflow-hidden bg-zinc-900 text-zinc-100"
      style={GRILLE_COCKPIT}
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
          alerte={cockpit.navRail.alerte}
        />
      </div>

      {/* Colonne latérale — col. 2, lignes 1-2.
          Nommée : depuis que le tableau des tickets occupe le centre, les
          mêmes titres apparaissent des deux côtés. Une assertion qui ne dit
          pas de quelle région elle parle en trouve deux. */}
      <aside
        aria-label="Panneau latéral"
        className="border-r border-zinc-700 overflow-hidden"
        style={{ gridColumn: "2", gridRow: "1 / 3" }}
      >
        <ErrorBoundary>
          <Sidebar panel={cockpit.panel} {...cockpit.sidebar} />
        </ErrorBoundary>
      </aside>

      {/* Centre — col. 3, ligne 1 */}
      <main
        aria-label="Vue principale"
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "1" }}
      >
        <ErrorBoundary>
          <CenterView panel={cockpit.panel} {...cockpit.centre} />
        </ErrorBoundary>
      </main>

      {/* Bandeau des événements — col. 3, ligne 2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "2" }}
      >
        <BottomPanel {...cockpit.bottomPanel} />
      </div>

      <ToastContainer toasts={cockpit.toasts} onDismiss={cockpit.fermerToast} />
    </div>
  );
}
