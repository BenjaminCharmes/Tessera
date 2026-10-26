import type { EtatBoite } from "../../lib/bureau/boiteAuxLettres";
import { TON_BOITE } from "./tons";

interface BoiteProps {
  etat: EtatBoite;
}

/**
 * La boîte aux lettres : son drapeau n'est levé que s'il y a une PR, et sa
 * teinte dit où elle en est (ADR-058). Grille 12 × 12.
 */
export default function Boite({ etat }: BoiteProps) {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 12 12"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="boite"
      data-boite={etat}
    >
      <rect x="5" y="8" width="2" height="4" className="fill-zinc-700" />
      <rect x="1" y="3" width="9" height="5" className="fill-zinc-600" />
      <rect x="2" y="4" width="5" height="1" className="fill-zinc-800" />
      {etat !== "aucune" && <rect x="10" y="1" width="1" height="5" className={TON_BOITE[etat]} />}
      {etat !== "aucune" && <rect x="8" y="1" width="2" height="2" className={TON_BOITE[etat]} />}
    </svg>
  );
}
