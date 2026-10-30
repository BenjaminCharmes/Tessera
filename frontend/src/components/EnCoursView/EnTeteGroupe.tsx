import type { GroupeDeProjet } from "./format";
import ArretDuProjet from "./ArretDuProjet";

interface EnTeteGroupeProps {
  groupe: GroupeDeProjet;
  /** Chaque app du groupe a déjà reçu son ordre d'arrêt. */
  enArret: boolean;
  onArreterProjet: () => void;
}

/** Le nom du projet et « Arrêter le projet » dans la vue en liste — ticket-424. */
export default function EnTeteGroupe({ groupe, enArret, onArreterProjet }: EnTeteGroupeProps) {
  return (
    <div className="mb-1 flex items-center gap-3">
      <h2 className="text-xs font-semibold text-zinc-400">{groupe.project_name}</h2>
      <ArretDuProjet groupe={groupe} enArret={enArret} onArreterProjet={onArreterProjet} />
    </div>
  );
}
