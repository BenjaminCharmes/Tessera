import { agentsDuService, useActiviteProduit } from "../../hooks/useActiviteProduit";
import type { AppEnCours } from "../../types/api";
import SalleDApp from "./SalleDApp";

interface SallesDesServeursProps {
  apps: AppEnCours[];
  lueA: number;
}

/**
 * Une salle par app de l'inventaire, aucune quand il est vide — ticket-672. Les agents
 * viennent du fichier d'activité du produit : sans lui, la salle n'en a pas (ticket-673).
 */
export default function SallesDesServeurs({ apps, lueA }: SallesDesServeursProps) {
  const activite = useActiviteProduit();
  return (
    <div data-vue="salles">
      {apps.map((app) => (
        <SalleDApp
          key={app.pid}
          app={app}
          lueA={lueA}
          agents={agentsDuService(activite, app.project_id, app.nom)}
        />
      ))}
    </div>
  );
}
