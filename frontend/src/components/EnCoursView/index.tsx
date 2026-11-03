import { useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import ViewSwitcher, { type OptionVue } from "../../design/ui/ViewSwitcher";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import type { ProjectOverview, RunActif } from "../../types/api";
import RegionTitle from "../../design/RegionTitle";
import EnTeteGroupe from "./EnTeteGroupe";
import LigneApp from "./LigneApp";
import ProjetsArretes from "./ProjetsArretes";
import SallesDesServeurs from "./SallesDesServeurs";
import SalleTessera from "./SalleTessera";
import { formaterMo, grouperParProjet, memoireTotale } from "./format";
import { useZoomDuBureau } from "../../hooks/useZoomDuBureau";
import { CommandesDeZoom } from "../SupervisionView/ZoomDuBureau";

type VueEnCours = "salles" | "liste";

const VUES: OptionVue<VueEnCours>[] = [
  { valeur: "salles", libelle: "Salles" },
  { valeur: "liste", libelle: "Liste" },
];

interface EnCoursViewProps {
  appsEnCours: UseAppsEnCoursResult;
  /** Les runs vivants de la supervision : une salle montre celui de son projet (ticket-712). */
  runs?: readonly RunActif[];
  /** La vue ouverte au départ : les salles, la liste restant au clavier et au lecteur d'écran. */
  vueInitiale?: VueEnCours;
}

const AUCUN: ProjectOverview[] = [];
const AUCUN_RUN: readonly RunActif[] = [];
const lireProjets = () => api.projects.overview();

function Message({ texte }: { texte: string }) {
  return <p className="p-8 text-center text-sm text-zinc-500">{texte}</p>;
}

/**
 * Les apps de projet qui tournent sur la machine — ticket-417.
 *
 * Vue globale, comme la supervision : elle ne dépend d'aucun projet actif.
 * L'état vient du cockpit (`useAppsEnCours`), qui relit toutes les 10 s.
 */
export default function EnCoursView({ appsEnCours, runs = AUCUN_RUN, vueInitiale = "salles" }: EnCoursViewProps) {
  const { apps, lueA, erreur, arreter, arreterProjet, lancer, enArret, enLancement } =
    appsEnCours;
  const { data: projets } = useResource(lireProjets, AUCUN);
  const [vue, setVue] = useState<VueEnCours>(vueInitiale);
  // Les salles des serveurs ont leur zoom, comme le Bureau (ticket-727).
  const {
    mode: modeDeZoom,
    defaut: zoomParDefaut,
    zoom,
    largeur,
    setMode: setModeDeZoom,
    conteneur,
    contenu,
  } = useZoomDuBureau({ cle: "salles.zoom", margeHorizontale: 32 });

  if (apps === null) {
    return erreur ? (
      <p role="alert" className="p-8 text-center text-sm text-red-300">
        {erreur}
      </p>
    ) : (
      <Message texte="Chargement…" />
    );
  }

  const enMarche = new Set(apps.map((app) => app.project_id));
  const arretes = projets.filter((p) => p.services_declares && !enMarche.has(p.id));

  return (
    <div className="flex h-full flex-col text-zinc-200">
      <header className="flex items-baseline justify-between px-4 pt-4 pb-3">
        <RegionTitle>En cours</RegionTitle>
        <span className="flex items-center gap-3 text-sm text-zinc-300">
          Mémoire totale : {formaterMo(memoireTotale(apps))}
          {vue === "salles" && (
            <CommandesDeZoom
              mode={modeDeZoom}
              zoom={zoom}
              setMode={setModeDeZoom}
              defaut={zoomParDefaut}
              vue="les salles"
            />
          )}
          <ViewSwitcher label="Vue des apps" options={VUES} valeur={vue} onChange={setVue} />
        </span>
      </header>
      <div ref={conteneur} className="min-h-0 flex-1 overflow-auto px-4 pb-4">
        {erreur && (
          <p role="alert" className="mb-3 text-sm text-red-300">
            {erreur}
          </p>
        )}
        {vue === "salles" && (
          // Le zoom ne touche que les salles : la liste des projets arrêtés garde sa taille.
          <div ref={contenu} data-zoom={zoom} style={{ zoom, width: largeur ?? undefined }}>
            <SalleTessera nom={projets.find((p) => p.id === "ide-core")?.name ?? "Tessera"} lueA={lueA} />
            {apps.length === 0 ? (
              <Message texte="Aucune app de projet ne tourne" />
            ) : (
              <SallesDesServeurs
                apps={apps}
                lueA={lueA}
                runs={runs}
                enArret={enArret}
                onArreterProjet={(id, groupe) => void arreterProjet(id, groupe)}
              />
            )}
          </div>
        )}
        {vue === "salles" ? null : apps.length === 0 ? (
          <Message texte="Aucune app de projet ne tourne" />
        ) : (
          grouperParProjet(apps).map((groupe) => (
            <section key={groupe.project_id} className="mb-4">
              <EnTeteGroupe
                groupe={groupe}
                enArret={groupe.apps.every((app) => enArret(app.pid))}
                onArreterProjet={() => void arreterProjet(groupe.project_id, groupe.apps)}
              />
              <ul className="rounded-sm bg-zinc-900 ring-1 ring-zinc-800">
                {groupe.apps.map((app) => (
                  <LigneApp
                    key={app.pid}
                    app={app}
                    now={lueA}
                    enArret={enArret(app.pid)}
                    onArreter={(pid) => void arreter(pid)}
                  />
                ))}
              </ul>
            </section>
          ))
        )}
        <ProjetsArretes
          projets={arretes}
          enLancement={enLancement}
          onLancer={(id) => void lancer(id)}
        />
      </div>
    </div>
  );
}
