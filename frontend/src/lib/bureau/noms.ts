import { TENUES, graine } from "./physique";
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
  const pris = new Set<number>();
  let choisi = 0;
  for (const r of ROLES) {
    choisi = premierLibre(graine(`${projet}:${r}`), pris);
    pris.add(choisi);
    if (r === role) break;
  }
  return PRENOMS[choisi] ?? PRENOMS[0];
}

/**
 * Le libellé d'un poste ou d'une activité précédé du prénom de l'agent :
 * « Camille, codeur, travaille » à partir de « Codeur, travaille ».
 */
export function avecLeNom(projet: string, role: RoleAffiche, libelle: string): string {
  const minuscule = libelle.charAt(0).toLowerCase() + libelle.slice(1);
  return `${nomDeLAgent(projet, role)}, ${minuscule}`;
}
