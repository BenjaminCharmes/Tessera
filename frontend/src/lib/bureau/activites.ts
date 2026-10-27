import { POSTES } from "./postesDuRun";
import type { PosteDuRun, PosteId } from "./postesDuRun";

/**
 * Ce que fait un agent qui a fini : café à son poste, une pause mains vides, ou la machine.
 * `fete` ne se tire jamais : la PR mergée la donne à tous, bras levés (ticket-598).
 * `copie` non plus : le refus du reviewer ou du validateur l'impose, feuille en main (ticket-599).
 */
export type Activite = "tasse" | "pause" | "machine" | "fete" | "copie";

/** Un tirage dans [0, 1[ : `Math.random` en production, une suite fixe dans les tests. */
export type Hasard = () => number;

export type Activites = Partial<Record<PosteId, Activite>>;

/** Trois places à la machine ; au-delà, l'agent boit son café à son poste. */
export const PLACES_MACHINE = 3;

/** Chance, à chaque tour d'horloge, qu'un agent change d'activité. */
export const CHANCE_DE_CHANGER = 0.25;

/** Le café à son poste pèse double, comme dans la maquette. */
const TIRAGE: readonly Activite[] = ["tasse", "tasse", "pause", "machine"];

const LIBELLES: Record<Activite, string> = {
  tasse: "boit un café à son poste",
  pause: "fait une pause",
  machine: "prend un café à la machine",
  fete: "fête la PR mergée",
  copie: "rend sa copie au codeur",
};

/** Sol de 800 px : les colonnes du grid (px-2.5, gap-1, cinq colonnes) donnent ces centres. */
const LARGEUR_COLONNE = 152.8;
const PAS_COLONNE = 156.8;
const MARGE_DU_SOL = 10;
/** Moitié du poste (56 px) plus la marge qui sépare l'agent debout de son bureau. */
const DECALAGE_A_COTE = 32;

/** Abscisse de la machine et de la porte, dans le fond de la pièce. */
export const MACHINE_X = 470;
export const PORTE_X = 752;
/** L'agent de 42 px se centre sur la porte de 36 px. */
const AGENT_A_LA_PORTE_X = PORTE_X - 3;
/** Autour de la machine : à gauche, à droite, puis plus loin à gauche. */
const PLACES_X = [MACHINE_X - 46, MACHINE_X + 50, MACHINE_X - 78] as const;

export type Niveau = "rangee" | "fond";

export interface AgentPlace {
  poste: PosteId;
  /** Abscisse du bord gauche de l'agent sur le sol de la pièce, en pixels. */
  x: number;
  /** `fond` : le long du mur (machine, porte) ; `rangee` : à hauteur des postes. */
  niveau: Niveau;
  /** `null` quand l'agent est parti : il n'a plus rien à faire dans la pièce. */
  activite: Activite | null;
  parti: boolean;
}

export function libelleActivite(activite: Activite): string {
  return LIBELLES[activite];
}

export function tirerActivite(hasard: Hasard): Activite {
  const indice = Math.min(TIRAGE.length - 1, Math.floor(hasard() * TIRAGE.length));
  return TIRAGE[indice] ?? "tasse";
}

/** Les postes dont l'agent a fini : eux seuls ont une activité (ADR-058). */
export function postesFaits(postes: readonly PosteDuRun[]): PosteId[] {
  return postes.filter((p) => p.etat === "fait").map((p) => p.poste);
}

/**
 * L'activité de chaque agent au tour suivant : celle qu'il avait, sauf une chance
 * sur quatre ou s'il n'en avait pas encore. Un agent qui n'a pas fini n'en garde aucune.
 */
export function renouveler(avant: Activites, faits: readonly PosteId[], hasard: Hasard): Activites {
  const suivantes: Activites = {};
  for (const poste of faits) {
    const actuelle = avant[poste];
    const garde = actuelle !== undefined && hasard() >= CHANCE_DE_CHANGER;
    suivantes[poste] = garde ? actuelle : tirerActivite(hasard);
  }
  return suivantes;
}

/**
 * Les activités après le plafond de la machine : les premiers postes, dans l'ordre
 * du pipeline, y entrent ; le suivant retombe sur le café à son poste.
 */
export function appliquerPlafond(brutes: Activites, faits: readonly PosteId[]): Activites {
  let places = PLACES_MACHINE;
  const effectives: Activites = {};
  for (const poste of POSTES) {
    if (!faits.includes(poste)) continue;
    const activite = brutes[poste] ?? "tasse";
    const entre = activite === "machine" && places > 0;
    if (entre) places -= 1;
    effectives[poste] = activite === "machine" && !entre ? "tasse" : activite;
  }
  return effectives;
}

function centreDuPoste(poste: PosteId): number {
  return MARGE_DU_SOL + POSTES.indexOf(poste) * PAS_COLONNE + LARGEUR_COLONNE / 2;
}

function placeDe(poste: PosteId, activite: Activite, rang: number): AgentPlace {
  if (activite === "machine") {
    const x = PLACES_X[rang] ?? PLACES_X[0];
    return { poste, x, niveau: "fond", activite, parti: false };
  }
  // Rendre sa copie : debout à côté du poste du codeur, pas du sien.
  const ancre = activite === "copie" ? "codeur" : poste;
  return { poste, x: centreDuPoste(ancre) + DECALAGE_A_COTE, niveau: "rangee", activite, parti: false };
}

/**
 * Où se tient chaque agent de la pièce. Run en cours : les agents qui ont fini,
 * chacun à sa place d'activité. Run clos : les cinq, à la porte (ADR-058 : ils
 * n'y sont que parce que le run est fini). PR mergée : les cinq, bras levés devant leur poste.
 * `copie` : l'agent qui a renvoyé le travail se tient au poste du codeur, feuille en main.
 */
export function placerLesAgents(
  faits: readonly PosteId[],
  effectives: Activites,
  clos: boolean,
  fete = false,
  copie: PosteId | null = null,
): AgentPlace[] {
  // La fête passe avant la porte : la PR se merge après la clôture du run (ADR-051).
  if (fete) return POSTES.map((poste) => placeDe(poste, "fete", 0));
  if (clos) {
    return POSTES.map((poste): AgentPlace => ({
      poste,
      x: AGENT_A_LA_PORTE_X,
      niveau: "fond",
      activite: null,
      parti: true,
    }));
  }
  let rang = 0;
  const places: AgentPlace[] = [];
  for (const poste of POSTES) {
    if (!faits.includes(poste)) continue;
    const activite = poste === copie ? "copie" : (effectives[poste] ?? "tasse");
    places.push(placeDe(poste, activite, rang));
    if (activite === "machine") rang += 1;
  }
  return places;
}

/** La machine fume quand quelqu'un s'y sert, et seulement alors. */
export function machineEnService(agents: readonly AgentPlace[]): boolean {
  return agents.some((a) => !a.parti && a.activite === "machine");
}
