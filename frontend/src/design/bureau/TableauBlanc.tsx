import type { EtatCase } from "../../lib/bureau/criteres";
import { CASES_MAX, tableauBlanc } from "../../lib/bureau/sprites/tableau";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

interface TableauBlancProps {
  /** Une entrée par critère, dans l'ordre du ticket. Vide : le tableau reste vierge. */
  cases: readonly EtatCase[];
}

const dessin = memoise((cases: string) => tableauBlanc(cases ? (cases.split(",") as EtatCase[]) : []));

/**
 * Le tableau blanc, grille 88 × 54 (ticket-727) : cadre alu, reflet, rebord à feutres.
 * Une case et une ligne manuscrite par critère, aux tons d'état (ADR-026) : grise en
 * attente, coche verte si le critère passe, croix rouge sinon (ADR-058). Au-delà de six,
 * une seconde colonne, douze au plus. `data-cases` dit ce qu'il montre ; le libellé
 * accessible est porté par l'objet qui l'enveloppe.
 */
export default function TableauBlanc({ cases }: TableauBlancProps) {
  const montrees = cases.slice(0, CASES_MAX).join(",");
  return (
    <SpriteSvg sprite={dessin(montrees)} largeur={88} hauteur={54} data-sprite="tableau-blanc" data-cases={montrees} />
  );
}
