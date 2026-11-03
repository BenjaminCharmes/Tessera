import type { Physique } from "./physique";
import type { RoleAffiche } from "./postesDuRun";

/** Le projet bootstrap : ses agents sont l'équipe de Tessera. */
export const PROJET_DE_TESSERA = "ide-core";

/** Un membre nommé de l'équipe : son prénom et son physique, fixés à la main. */
export interface MembreDeLEquipe {
  prenom: string;
  physique: Physique;
}

/**
 * L'équipe de Tessera, choisie par Benjamin le 30/10. Ces rôles ne tirent ni leur
 * prénom ni leur physique de la graine : ce sont des personnes, toujours les mêmes.
 * Les rôles absents gardent le tirage ordinaire (`nomDeLAgent`, `physique`).
 */
export const EQUIPE_DE_TESSERA: Partial<Record<RoleAffiche, MembreDeLEquipe>> = {
  // Homme brun.
  codeur: { prenom: "Maxime", physique: { peau: 2, cheveux: 1, coiffure: "court", jupe: false } },
  // Homme à la peau claire, blond.
  testeur: { prenom: "Giovanni", physique: { peau: 1, cheveux: 7, coiffure: "court", jupe: false } },
  // Homme noir, cheveux bruns.
  securite: { prenom: "Garrett", physique: { peau: 5, cheveux: 6, coiffure: "court", jupe: false } },
  // Homme très bronzé, cheveux noirs.
  reviewer: { prenom: "Lorenzo", physique: { peau: 4, cheveux: 2, coiffure: "court", jupe: false } },
};

/** Le membre de l'équipe qui tient ce rôle sur ce projet, s'il est nommé. */
export function membreDeLEquipe(projet: string, role: RoleAffiche): MembreDeLEquipe | undefined {
  return projet === PROJET_DE_TESSERA ? EQUIPE_DE_TESSERA[role] : undefined;
}
