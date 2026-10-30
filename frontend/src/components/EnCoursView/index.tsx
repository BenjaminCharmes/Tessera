import { useState } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import ViewSwitcher, { type OptionVue } from "../../design/ui/ViewSwitcher";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import type { ProjectOverview } from "../../types/api";
import RegionTitle from "../../design/RegionTitle";
import EnTeteGroupe from "./EnTeteGroupe";
import LigneApp from "./LigneApp";
import ProjetsArretes from "./ProjetsArretes";
import SallesDesServeurs from "./SallesDesServeurs";
import SalleTessera from "./SalleTessera";
import { formaterMo, grouperParProjet, memoireTotale } from "./format";

type VueEnCours = "salles" | "liste";

const VUES: OptionVue<VueEnCours>[] = [
  { valeur: "salles", libelle: "Salles" },
  { valeur: "liste", libelle: "Liste" },
];

interface EnCoursViewProps {
  appsEnCours: UseAppsEnCoursResult;
  /** La vue ouverte au départ : les salles, la liste restant au clavier et au lecteur d'écran. */
  vueInitiale?: VueEnCours;
}

const AUCUN: ProjectOverview[] = [];
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
export default function EnCoursView({ appsEnCours, vueInitiale = "salles" }: EnCoursViewProps) {
  const { apps, lueA, erreur, arreter, arreterProjet, lancer, enArret, enLancement } =
    appsEnCours;
  const { data: projets } = useResource(lireProjets, AUCUN);
  const [vue, setVue] = useState<VueEnCours>(vueInitiale);

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
    <div className="h-full overflow-y-auto p-4 text-zinc-200">
      <header className="mb-3 flex items-baseline justify-between">
        <RegionTitle>En cours</RegionTitle>
        <span className="flex items-center gap-3 text-sm text-zinc-300">
          Mémoire totale : {formaterMo(memoireTotale(apps))}
          <ViewSwitcher label="Vue des apps" options={VUES} valeur={vue} onChange={setVue} />
        </span>
      </header>
      {erreur && (
        <p role="alert" className="mb-3 text-sm text-red-300">
          {erreur}
        </p>
      )}
      {vue === "salles" && (
        <SalleTessera nom={projets.find((p) => p.id === "ide-core")?.name ?? "Tessera"} lueA={lueA} />
      )}
      {apps.length === 0 ? (
        <Message texte="Aucune app de projet ne tourne" />
      ) : vue === "salles" ? (
        <SallesDesServeurs
          apps={apps}
          lueA={lueA}
          enArret={enArret}
          onArreterProjet={(id, groupe) => void arreterProjet(id, groupe)}
        />
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
  );
}
