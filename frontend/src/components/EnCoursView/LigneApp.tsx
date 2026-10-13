import { useState } from "react";
import type { AppEnCours } from "../../types/api";
import { formaterDuree, formaterMo } from "./format";

interface LigneAppProps {
  app: AppEnCours;
  now: number;
  onArreter: (pid: number) => void;
}

const ORIGINES: Record<AppEnCours["origine"], string> = {
  tessera: "Tessera",
  externe: "Lancé à la main",
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
function Arret({ app, onArreter }: Pick<LigneAppProps, "app" | "onArreter">) {
  const [confirmation, setConfirmation] = useState(false);
  const bouton = "rounded-sm px-2 py-1 text-xs";

  if (!confirmation) {
    const arreter = () =>
      app.origine === "externe" ? setConfirmation(true) : onArreter(app.pid);
    return (
      <button
        type="button"
        onClick={arreter}
        aria-label={`Arrêter ${app.nom}`}
        className={`${bouton} bg-zinc-700 text-zinc-200 hover:bg-zinc-600`}
      >
        Arrêter
      </button>
    );
  }
  return (
    <span className="flex items-center gap-2 text-xs text-zinc-300">
      <span>Arrêter le processus {app.pid} ?</span>
      <button
        type="button"
        onClick={() => {
          setConfirmation(false);
          onArreter(app.pid);
        }}
        className={`${bouton} bg-red-500/20 text-red-200 hover:bg-red-500/30`}
      >
        Confirmer
      </button>
      <button
        type="button"
        onClick={() => setConfirmation(false)}
        className={`${bouton} bg-zinc-700 text-zinc-200 hover:bg-zinc-600`}
      >
        Annuler
      </button>
    </span>
  );
}

export default function LigneApp({ app, now, onArreter }: LigneAppProps) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-zinc-800 px-3 py-2 text-sm">
      <span className="min-w-32 font-medium text-zinc-100">{app.nom}</span>
      <span className="rounded-sm bg-zinc-800 px-1.5 py-0.5 text-micro text-zinc-400">
        {ORIGINES[app.origine]}
      </span>
      <Ports ports={app.ports} />
      <span className="text-zinc-400">{formaterDuree(app.demarre_a, now)}</span>
      <span className="ml-auto tabular-nums text-zinc-200">
        {formaterMo(app.memoire_mo)}
      </span>
      <Arret app={app} onArreter={onArreter} />
    </li>
  );
}
