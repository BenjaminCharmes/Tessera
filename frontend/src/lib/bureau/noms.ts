import { TENUES, graine } from "./physique";
import { membreDeLEquipe } from "./equipeDeTessera";
import type { RoleAffiche } from "./postesDuRun";

/** Les prénoms que le Bureau donne à ses agents : une liste fixe, plus longue que les neuf rôles. */
const PRENOMS: readonly [string, ...string[]] = [
  "Camille",
  "Alexis",
  "Sasha",
  "Charlie",
  "Dominique",
  "Morgan",
  "Andrea",
  "Maxime",
  "Louison",
  "Noé",
  "Océane",
  "Eden",
  "Gabin",
  "Inès",
  "Jules",
  "Léa",
  "Mathis",
  "Nina",
  "Oscar",
  "Paloma",
  "Quentin",
  "Rémi",
  "Salomé",
  "Théo",
  "Ulysse",
  "Valentine",
  "Yanis",
  "Zoé",
  "Anouk",
  "Basile",
  "Clémence",
  "Dario",
];

const ROLES = Object.keys(TENUES) as RoleAffiche[];

/** Le premier prénom libre à partir de celui que la graine désigne : les rôles ne se partagent jamais un prénom. */
function premierLibre(depart: number, pris: ReadonlySet<number>): number {
  let i = depart % PRENOMS.length;
  while (pris.has(i)) i = (i + 1) % PRENOMS.length;
  return i;
}

/**
 * Le prénom d'un agent : le même `projet` et le même `role` rendent toujours le
 * même prénom, avec la graine de `physique`. Les rôles se départagent dans un
 * ordre fixe, si bien que deux rôles d'un même projet ne se confondent jamais.
 * Un nom est une identité, comme la tenue : il ne dit rien de l'état du run.
 */
export function nomDeLAgent(projet: string, role: RoleAffiche): string {
  const membre = membreDeLEquipe(projet, role);
  if (membre) return membre.prenom;
  // Les prénoms de l'équipe nommée ne se tirent plus pour les autres rôles du projet.
  const pris = new Set<number>(
    ROLES.map((r) => membreDeLEquipe(projet, r)?.prenom)
      .map((p) => (p === undefined ? -1 : PRENOMS.indexOf(p)))
      .filter((i) => i >= 0),
  );
  let choisi = 0;
  for (const r of ROLES) {
    if (membreDeLEquipe(projet, r)) continue;
    choisi = premierLibre(graine(`${projet}:${r}`), pris);
    pris.add(choisi);
    if (r === role) break;
  }
  return PRENOMS[choisi] ?? PRENOMS[0];
}

/**
 * Le personnel des salles communes : une personne chacun, un prénom fixe. Hors de
 * `PRENOMS`, pour ne jamais se confondre avec un agent de projet. Le directeur,
 * c'est l'utilisateur lui-même : il s'appelle Ben.
 */
export const NOM_DU_DIRECTEUR = "Ben";
export const NOM_DES_RH = "Hélène";

/**
 * Le libellé d'un poste ou d'une activité précédé du prénom de l'agent :
 * « Camille, codeur, travaille » à partir de « Codeur, travaille ».
 */
export function avecLeNom(projet: string, role: RoleAffiche, libelle: string): string {
  const minuscule = libelle.charAt(0).toLowerCase() + libelle.slice(1);
  return `${nomDeLAgent(projet, role)}, ${minuscule}`;
}

/**
 * Un agent de passage dans une salle commune : son prénom, son poste et son projet,
 * puisque la salle reçoit tous les projets. « Camille, codeur · curio ».
 */
export function visiteur(projet: string, role: RoleAffiche, poste: string): string {
  return `${avecLeNom(projet, role, poste)} · ${projet}`;
}

/**
 * Le prénom d'un agent de produit (ticket-673) : une identité tirée de la même
 * graine que sa tenue (`physiqueDeProduit`), stable d'un rendu à l'autre. Ses
 * voisins du même projet se départagent dans l'ordre où le produit les déclare.
 */
export function prenomsDeProduit(projet: string, ids: readonly string[]): Map<string, string> {
  const pris = new Set<number>();
  const prenoms = new Map<string, string>();
  for (const id of ids) {
    const choisi = premierLibre(graine(`${projet}:produit:${id}`), pris);
    pris.add(choisi);
    prenoms.set(id, PRENOMS[choisi] ?? PRENOMS[0]);
  }
  return prenoms;
}
