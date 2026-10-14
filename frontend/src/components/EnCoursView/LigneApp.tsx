import { useState } from "react";
import type { AppEnCours } from "../../types/api";
import { formaterDuree, formaterMo } from "./format";
import Button from "../../design/ui/Button";
import StatusPill, { type EtatPastille } from "../../design/ui/StatusPill";
import Spinner from "./Spinner";

interface LigneAppProps {
  app: AppEnCours;
  now: number;
  /** L'ordre d'arrêt est parti ; le pid est encore dans l'inventaire. */
  enArret: boolean;
  onArreter: (pid: number) => void;
}

const ORIGINES: Record<AppEnCours["origine"], { etat: EtatPastille; libelle: string }> = {
  tessera: { etat: "en-cours", libelle: "Tessera" },
  // Une app lancée à la main demande une confirmation avant l'arrêt.
  externe: { etat: "attention", libelle: "Lancé à la main" },
};

function Ports({ ports }: { ports: number[] }) {
  if (ports.length === 0) return <span className="text-zinc-500">—</span>;
  return (
    <span className="flex gap-2">
      {ports.map((port) => (
        <a
          key={port}
          href={`http://localhost:${port}`}
          target="_blank"
          rel="noreferrer"
          className="text-blue-300 hover:underline"
        >
          localhost:{port}
        </a>
      ))}
    </span>
  );
}

/** Le bouton « Arrêter » ; une app lancée à la main demande d'abord confirmation. */
function Arret({ app, enArret, onArreter }: Pick<LigneAppProps, "app" | "enArret" | "onArreter">) {
  const [confirmation, setConfirmation] = useState(false);

  if (enArret) {
    return (
      <Button variante="arret" taille="compact" disabled aria-label={`Arrêter ${app.nom}`}>
        <Spinner />
        Arrêt…
      </Button>
    );
  }

  if (!confirmation) {
    const arreter = () =>
      app.origine === "externe" ? setConfirmation(true) : onArreter(app.pid);
    return (
      <Button
        variante="arret"
        taille="compact"
        onClick={arreter}
        aria-label={`Arrêter ${app.nom}`}
      >
        Arrêter
      </Button>
    );
  }
  return (
    <span className="flex items-center gap-2 text-xs text-zinc-300">
      <span>Arrêter le processus {app.pid} ?</span>
      <Button
        variante="arret"
        taille="compact"
        onClick={() => {
          setConfirmation(false);
          onArreter(app.pid);
        }}
      >
        Confirmer
      </Button>
      <Button variante="discret" taille="compact" onClick={() => setConfirmation(false)}>
        Annuler
      </Button>
    </span>
  );
}

export default function LigneApp({ app, now, enArret, onArreter }: LigneAppProps) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-zinc-800 px-3 py-2 text-sm">
      <span className="min-w-32 font-medium text-zinc-100">{app.nom}</span>
      <StatusPill etat={ORIGINES[app.origine].etat} libelle={ORIGINES[app.origine].libelle} />
      <Ports ports={app.ports} />
      <span className="text-zinc-400">{formaterDuree(app.demarre_a, now)}</span>
      <span className="ml-auto tabular-nums text-zinc-200">
        {formaterMo(app.memoire_mo)}
      </span>
      <Arret app={app} enArret={enArret} onArreter={onArreter} />
    </li>
  );
}
