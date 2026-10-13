import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import RegionTitle from "../../design/RegionTitle";
import LigneApp from "./LigneApp";
import { formaterMo, grouperParProjet, memoireTotale } from "./format";

interface EnCoursViewProps {
  appsEnCours: UseAppsEnCoursResult;
}

function Message({ texte }: { texte: string }) {
  return <p className="p-8 text-center text-sm text-zinc-500">{texte}</p>;
}

/**
 * Les apps de projet qui tournent sur la machine — ticket-417.
 *
 * Vue globale, comme la supervision : elle ne dépend d'aucun projet actif.
 * L'état vient du cockpit (`useAppsEnCours`), qui relit toutes les 10 s.
 */
export default function EnCoursView({ appsEnCours }: EnCoursViewProps) {
  const { apps, lueA, erreur, arreter } = appsEnCours;

  if (apps === null) {
    return erreur ? (
      <p role="alert" className="p-8 text-center text-sm text-red-300">
        {erreur}
      </p>
    ) : (
      <Message texte="Chargement…" />
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 text-zinc-200">
      <header className="mb-3 flex items-baseline justify-between">
        <RegionTitle>En cours</RegionTitle>
        <span className="text-sm text-zinc-300">
          Mémoire totale : {formaterMo(memoireTotale(apps))}
        </span>
      </header>
      {erreur && (
        <p role="alert" className="mb-3 text-sm text-red-300">
          {erreur}
        </p>
      )}
      {apps.length === 0 ? (
        <Message texte="Aucune app de projet ne tourne" />
      ) : (
        grouperParProjet(apps).map((groupe) => (
          <section key={groupe.project_id} className="mb-4">
            <h2 className="mb-1 text-xs font-semibold text-zinc-400">
              {groupe.project_name}
            </h2>
            <ul className="rounded-sm bg-zinc-900 ring-1 ring-zinc-800">
              {groupe.apps.map((app) => (
                <LigneApp
                  key={app.pid}
                  app={app}
                  now={lueA}
                  onArreter={(pid) => void arreter(pid)}
                />
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
