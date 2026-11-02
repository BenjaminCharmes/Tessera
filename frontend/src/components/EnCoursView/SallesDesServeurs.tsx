import { agentsDuService, useActiviteProduit } from "../../hooks/useActiviteProduit";
import type { AppEnCours, RunActif } from "../../types/api";
import { grouperParProjet } from "./format";
import SalleDeProjet from "./SalleDeProjet";

interface SallesDesServeursProps {
  apps: AppEnCours[];
  lueA: number;
  /** Les runs vivants, tous projets confondus : chaque salle prend celui de son projet. */
  runs?: readonly RunActif[];
  enArret: (pid: number) => boolean;
  onArreterProjet: (projectId: string, apps: AppEnCours[]) => void;
}

const AUCUN_RUN: readonly RunActif[] = [];

/**
 * Une salle par projet lancé, en grille — tickets 672, 710 et 712. Les agents viennent
 * du fichier d'activité du produit : sans lui, la salle n'en a pas (ticket-673).
 */
export default function SallesDesServeurs({ apps, lueA, runs = AUCUN_RUN, enArret, onArreterProjet }: SallesDesServeursProps) {
  const activite = useActiviteProduit();
  return (
    <div data-vue="salles" className="mb-4 grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
      {grouperParProjet(apps).map((groupe) => (
        <SalleDeProjet
          key={groupe.project_id}
          groupe={groupe}
          lueA={lueA}
          run={runs.find((r) => r.project_id === groupe.project_id)}
          agents={groupe.apps.flatMap((app) =>
            agentsDuService(activite, app.project_id, app.nom).map((agent) => ({ service: app.nom, agent })),
          )}
          enArret={groupe.apps.every((app) => enArret(app.pid))}
          onArreterProjet={() => onArreterProjet(groupe.project_id, groupe.apps)}
        />
      ))}
    </div>
  );
}
