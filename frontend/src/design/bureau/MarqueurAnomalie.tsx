import { marqueurAnomalie } from "../../lib/bureau/sprites/objets";
import { memoise } from "../../lib/bureau/sprites/symboles";
import { libelleDesAnomalies } from "../../lib/bureau/marqueurAnomalie";
import SpriteSvg from "./SpriteSvg";

interface MarqueurAnomalieProps {
  /** Le nombre d'anomalies du run : il entre dans le nom accessible, jamais dans le dessin. */
  nombre: number;
}

const dessin = memoise(marqueurAnomalie);

/**
 * Le marqueur d'une anomalie, grille 9 × 8 (ADR-078, ticket-832) : un triangle ambre au-dessus
 * du poste de l'agent. Un par run, quel que soit le nombre d'anomalies ; le sprite est un
 * `<use>` du `<defs>` commun, il n'ajoute aucun chemin en ligne (ADR-070).
 */
export default function MarqueurAnomalie({ nombre }: MarqueurAnomalieProps) {
  const libelle = libelleDesAnomalies(nombre);
  return (
    <span role="img" aria-label={libelle} title={libelle} data-testid="marqueur-anomalie" className="mb-0.5 inline-flex">
      <SpriteSvg sprite={dessin()} largeur={18} hauteur={16} data-sprite="anomalie" data-anomalies={nombre} />
    </span>
  );
}
