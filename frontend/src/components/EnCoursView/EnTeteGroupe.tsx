import { useState } from "react";
import type { GroupeDeProjet } from "./format";
import Spinner from "./Spinner";

interface EnTeteGroupeProps {
  groupe: GroupeDeProjet;
  /** Chaque app du groupe a déjà reçu son ordre d'arrêt. */
  enArret: boolean;
  onArreterProjet: () => void;
}

const BOUTON = "rounded-sm px-2 py-1 text-xs";

/**
 * Le nom du projet et « Arrêter le projet » — ticket-424.
 *
 * Une seule confirmation, qui liste les pids des apps lancées à la main : un
 * groupe fait de services Tessera seuls s'arrête sans demander.
 */
export default function EnTeteGroupe({ groupe, enArret, onArreterProjet }: EnTeteGroupeProps) {
  const [confirmation, setConfirmation] = useState(false);
  const externes = groupe.apps.filter((app) => app.origine === "externe");
  const lancer = () => {
    setConfirmation(false);
    onArreterProjet();
  };

  return (
    <div className="mb-1 flex items-center gap-3">
      <h2 className="text-xs font-semibold text-zinc-400">{groupe.project_name}</h2>
      {confirmation ? (
        <span className="flex items-center gap-2 text-xs text-zinc-300">
          <span>
            Arrêter aussi les processus lancés à la main ({externes.map((a) => a.pid).join(", ")}) ?
          </span>
          <button
            type="button"
            onClick={lancer}
            className={`${BOUTON} bg-red-500/20 text-red-200 hover:bg-red-500/30`}
          >
            Confirmer l&apos;arrêt du projet
          </button>
          <button
            type="button"
            onClick={() => setConfirmation(false)}
            className={`${BOUTON} bg-zinc-700 text-zinc-200 hover:bg-zinc-600`}
          >
            Annuler l&apos;arrêt du projet
          </button>
        </span>
      ) : (
        <button
          type="button"
          disabled={enArret}
          onClick={() => (externes.length > 0 ? setConfirmation(true) : lancer())}
          aria-label={`Arrêter le projet ${groupe.project_name}`}
          className={`${BOUTON} flex items-center gap-1.5 bg-zinc-700 text-zinc-200 hover:bg-zinc-600 disabled:opacity-60`}
        >
          {enArret && <Spinner />}
          {enArret ? "Arrêt…" : "Arrêter le projet"}
        </button>
      )}
    </div>
  );
}
