import { BIBLIOTHEQUE_X } from "./activites";
import type { Placement } from "./activites";
import type { RoleSansPoste } from "./postesDuRun";

/** Les deux rédacteurs de la documentation par lot (ADR-035), dans l'ordre où ils se tiennent. */
export const REDACTEURS = ["doc-technique", "doc-fonctionnelle"] as const satisfies readonly RoleSansPoste[];

export type RoleDeRedaction = (typeof REDACTEURS)[number];

export interface RedacteurPlace extends Placement {
  role: RoleDeRedaction;
}

/**
 * Les bords gauches des deux rédacteurs par rapport à la bibliothèque (72 px d'écran) :
 * chacun déborde d'un côté, pour qu'on les voie l'un à côté de l'autre sans qu'ils se masquent.
 */
const DECALAGES_A_LA_BIBLIOTHEQUE: Record<RoleDeRedaction, number> = {
  "doc-technique": -40,
  "doc-fonctionnelle": 32,
};

/**
 * Où se tiennent les rédacteurs : debout devant la bibliothèque tant que la
 * documentation tourne, personne sinon (ADR-058 : on ne dessine que ce qui est vrai).
 */
export function placerLesRedacteurs(documentation: boolean): RedacteurPlace[] {
  if (!documentation) return [];
  return REDACTEURS.map((role) => ({
    role,
    x: BIBLIOTHEQUE_X,
    decalage: DECALAGES_A_LA_BIBLIOTHEQUE[role],
    niveau: "fond",
    activite: "redige",
    parti: false,
  }));
}
