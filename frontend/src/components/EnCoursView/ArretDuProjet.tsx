import { useState } from "react";
import type { GroupeDeProjet } from "./format";
import Button from "../../design/ui/Button";
import Spinner from "./Spinner";

interface ArretDuProjetProps {
  groupe: GroupeDeProjet;
  /** Chaque app du groupe a déjà reçu son ordre d'arrêt. */
  enArret: boolean;
  onArreterProjet: () => void;
}

/**
 * « Arrêter le projet » — ticket-424, partagé par la liste et les salles (ticket-710).
 *
 * Une seule confirmation, qui liste les pids des apps lancées à la main : un
 * groupe fait de services Tessera seuls s'arrête sans demander.
 */
export default function ArretDuProjet({ groupe, enArret, onArreterProjet }: ArretDuProjetProps) {
  const [confirmation, setConfirmation] = useState(false);
  const externes = groupe.apps.filter((app) => app.origine === "externe");
  const lancer = () => {
    setConfirmation(false);
    onArreterProjet();
  };

  if (confirmation) {
    return (
      <span className="flex flex-wrap items-center gap-2 text-xs text-zinc-300">
        <span>
          Arrêter aussi les processus lancés à la main ({externes.map((a) => a.pid).join(", ")}) ?
        </span>
        <Button variante="arret" taille="compact" onClick={lancer}>
          Confirmer l&apos;arrêt du projet
        </Button>
        <Button variante="discret" taille="compact" onClick={() => setConfirmation(false)}>
          Annuler l&apos;arrêt du projet
        </Button>
      </span>
    );
  }
  return (
    <Button
      variante="arret"
      taille="compact"
      disabled={enArret}
      onClick={() => (externes.length > 0 ? setConfirmation(true) : lancer())}
      aria-label={`Arrêter le projet ${groupe.project_name}`}
    >
      {enArret && <Spinner />}
      {enArret ? "Arrêt…" : "Arrêter le projet"}
    </Button>
  );
}
