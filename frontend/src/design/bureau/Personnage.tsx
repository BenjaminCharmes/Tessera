import type { Physique, Tenue } from "../../lib/bureau/physique";
import PersonnageAssis from "./PersonnageAssis";
import PersonnageDebout from "./PersonnageDebout";

interface PersonnageProps {
  /** La tenue de son rôle : couleur du haut, capuche, cravate. */
  tenue: Tenue;
  /** Son physique, tiré de `projet:rôle` : peau, cheveux, coiffure, jupe. */
  physique: Physique;
  /** Les mains tapent : vrai quand l'agent travaille. */
  tape?: boolean;
  /** Assis au poste (défaut), ou debout à côté, tasse à la main : l'agent a fini. */
  pose?: "assis" | "debout";
}

/**
 * Le personnage d'un poste : assis (grille 16 × 18 du poste, immobile ou à
 * taper), ou debout une fois fini (grille 12 × 20). Même échelle, même tête.
 */
export default function Personnage({ tenue, physique, tape = false, pose = "assis" }: PersonnageProps) {
  if (pose === "debout") return <PersonnageDebout tenue={tenue} physique={physique} />;
  return <PersonnageAssis tenue={tenue} physique={physique} tape={tape} />;
}
