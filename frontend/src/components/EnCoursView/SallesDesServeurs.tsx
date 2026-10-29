import type { AppEnCours } from "../../types/api";
import SalleDApp from "./SalleDApp";

interface SallesDesServeursProps {
  apps: AppEnCours[];
  lueA: number;
}

/** Une salle par app de l'inventaire, aucune quand il est vide — ticket-672. */
export default function SallesDesServeurs({ apps, lueA }: SallesDesServeursProps) {
  return (
    <div data-vue="salles">
      {apps.map((app) => (
        <SalleDApp key={app.pid} app={app} lueA={lueA} />
      ))}
    </div>
  );
}
