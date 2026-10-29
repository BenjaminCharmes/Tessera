import { POSTES } from "./postesDuRun";
import type { PosteDuRun, PosteId } from "./postesDuRun";

/**
 * Ce que fait un agent qui a fini : café à son poste, une pause mains vides, ou la machine.
 * `fete` ne se tire jamais : la PR mergée la donne à tous, bras levés (ticket-598).
 * `copie` non plus : le refus du reviewer ou du validateur l'impose, feuille en main (ticket-599).
 * `plan` non plus : le tour de plan l'impose, debout devant le tableau blanc (ticket-623).
 * `depose` : la livraison l'impose au codeur, devant la boîte aux lettres ; `redige` : la
 * documentation l'impose à ses deux rédacteurs, devant la bibliothèque (ticket-624).
 */
export type Activite =
  | "tasse"
  | "pause"
  | "machine"
  | "fete"
  | "copie"
  | "plan"
  | "depose"
  | "redige";

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
  plan: "prépare le plan",
  depose: "dépose la PR",
  redige: "rédige la documentation",
};

/** Sol de 800 px : les colonnes du grid (px-2.5, gap-1, cinq colonnes) donnent ces centres. */
const LARGEUR_COLONNE = 152.8;
const PAS_COLONNE = 156.8;
const MARGE_DU_SOL = 10;
/**
 * Les décalages se comptent en pixels d'écran, sprites agrandis (×1,5) : ils ne
 * s'étirent pas avec le sol, contrairement aux abscisses du repère.
 * Moitié du poste (84 px) plus la marge qui sépare l'agent debout de son bureau.
 */
export const DECALAGE_A_COTE = 48;

/** Abscisse de la machine et de la porte, dans le fond de la pièce. */
export const MACHINE_X = 470;
/** La bibliothèque, entre les deux premières fenêtres (ticket-627). */
export const BIBLIOTHEQUE_X = 208;
/** Le bord gauche du tableau blanc, au mur : l'agent du plan s'y tient. */
export const TABLEAU_X = 30;
/**
 * Le tableau fait 88 px × 1,5 × 1,15 d'écran ; l'agent, 63 px : pour le centrer
 * devant, son bord gauche se décale de la moitié de la différence.
 */
const DECALAGE_AU_TABLEAU = 44;
export const PORTE_X = 738;
/** La boîte aux lettres, au mur : le codeur y dépose la PR (ticket-624). */
export const BOITE_X = 676;
/** Devant la boîte (agent de 63 px), à sa gauche : la porte et l'interrupteur sont à sa droite. */
const DECALAGE_A_LA_BOITE = -50;
/** L'agent de 63 px se centre sur la porte de 81 px. */
const DECALAGE_A_LA_PORTE = 9;
/** Autour de la machine (54 px) : à gauche, à droite, puis plus loin à gauche. */
const PLACES_A_LA_MACHINE = [-66, 58, -132] as const;

export type Niveau = "rangee" | "fond";

/** Où se tient un personnage debout dans la pièce, poste ou non. */
export interface Placement {
  /** L'abscisse de son ancre (poste, machine, porte), dans le repère de 800 px. */
  x: number;
  /** Le bord gauche de l'agent par rapport à l'ancre, en pixels d'écran : il ne s'étire pas. */
  decalage: number;
  /** `fond` : le long du mur (machine, porte) ; `rangee` : à hauteur des postes. */
  niveau: Niveau;
  /** `null` quand l'agent est parti : il n'a plus rien à faire dans la pièce. */
  activite: Activite | null;
  parti: boolean;
}

export interface AgentPlace extends Placement {
  poste: PosteId;
}

export function libelleActivite(activite: Activite): string {
  return LIBELLES[activite];
}

export function tirerActivite(hasard: Hasard): Activite {
  const indice = Math.min(
    TIRAGE.length - 1,
    Math.floor(hasard() * TIRAGE.length),
  );
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
export function renouveler(
  avant: Activites,
  faits: readonly PosteId[],
  hasard: Hasard,
): Activites {
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
export function appliquerPlafond(
  brutes: Activites,
  faits: readonly PosteId[],
): Activites {
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

/** Le centre d'un poste dans le repère de 800 px : l'ancre des agents debout et du directeur en visite. */
export function centreDuPoste(poste: PosteId): number {
  return (
    MARGE_DU_SOL + POSTES.indexOf(poste) * PAS_COLONNE + LARGEUR_COLONNE / 2
  );
}

function placeDe(poste: PosteId, activite: Activite, rang: number): AgentPlace {
  if (activite === "machine") {
    const decalage = PLACES_A_LA_MACHINE[rang] ?? PLACES_A_LA_MACHINE[0];
    return {
      poste,
      x: MACHINE_X,
      decalage,
      niveau: "fond",
      activite,
      parti: false,
    };
  }
  if (activite === "plan") {
    return {
      poste,
      x: TABLEAU_X,
      decalage: DECALAGE_AU_TABLEAU,
      niveau: "fond",
      activite,
      parti: false,
    };
  }
  if (activite === "depose") {
    return {
      poste,
      x: BOITE_X,
      decalage: DECALAGE_A_LA_BOITE,
      niveau: "fond",
      activite,
      parti: false,
    };
  }
  // Rendre sa copie : debout à côté du poste du codeur, pas du sien.
  const ancre = activite === "copie" ? "codeur" : poste;
  return {
    poste,
    x: centreDuPoste(ancre),
    decalage: DECALAGE_A_COTE,
    niveau: "rangee",
    activite,
    parti: false,
  };
}

/** Ce qu'un événement du run impose à un agent, quoi que le tirage ait donné. */
interface Imposees {
  copie: PosteId | null;
  plan: PosteId | null;
  /** La livraison tourne : le codeur dépose la PR. */
  livraison: boolean;
}

/** Le poste que la livraison fait sortir de son bureau : celui du codeur. */
export const POSTE_DE_LA_LIVRAISON: PosteId = "codeur";

/** Le plan, la dépose et la copie s'imposent à l'agent ; sinon, l'activité tirée, café à son poste par défaut. */
function activiteDe(poste: PosteId, effectives: Activites, imposees: Imposees): Activite {
  if (poste === imposees.plan) return "plan";
  if (imposees.livraison && poste === POSTE_DE_LA_LIVRAISON) return "depose";
  return poste === imposees.copie ? "copie" : (effectives[poste] ?? "tasse");
}

/**
 * Où se tient chaque agent de la pièce. Run en cours : les agents qui ont fini,
 * chacun à sa place d'activité. Run clos : les cinq, à la porte (ADR-058 : ils
 * n'y sont que parce que le run est fini). PR mergée : les cinq, bras levés devant leur poste.
 * `copie` : l'agent qui a renvoyé le travail se tient au poste du codeur, feuille en main.
 * `plan` : l'agent du tour de plan, qui n'a pas fini, se tient devant le tableau blanc.
 * `livraison` : pendant la phase 1, le codeur se tient devant la boîte aux lettres.
 */
export function placerLesAgents(
  faits: readonly PosteId[],
  effectives: Activites,
  clos: boolean,
  fete = false,
  copie: PosteId | null = null,
  plan: PosteId | null = null,
  livraison = false,
): AgentPlace[] {
  const imposees: Imposees = { copie, plan, livraison };
  // La fête passe avant la porte : la PR se merge après la clôture du run (ADR-051).
  if (fete) return POSTES.map((poste) => placeDe(poste, "fete", 0));
  if (clos) {
    return POSTES.map((poste): AgentPlace => ({
      poste,
      x: PORTE_X,
      decalage: DECALAGE_A_LA_PORTE,
      niveau: "fond",
      activite: null,
      parti: true,
    }));
  }
  let rang = 0;
  const places: AgentPlace[] = [];
  for (const poste of POSTES) {
    const impose = poste === plan || (livraison && poste === POSTE_DE_LA_LIVRAISON);
    if (!faits.includes(poste) && !impose) continue;
    const activite = activiteDe(poste, effectives, imposees);
    places.push(placeDe(poste, activite, rang));
    if (activite === "machine") rang += 1;
  }
  return places;
}

/**
 * Les agents qui bavardent : au moins deux à la machine, côte à côte. Le premier
 * arrivé parle (ADR-058 : la bulle dit un fait, deux agents en pause ensemble).
 */
export function quiBavarde(agents: readonly AgentPlace[]): PosteId | null {
  const aLaMachine = agents.filter((a) => !a.parti && a.activite === "machine");
  return aLaMachine.length >= 2 ? (aLaMachine[0]?.poste ?? null) : null;
}

/** La machine fume quand quelqu'un s'y sert, et seulement alors. */
export function machineEnService(agents: readonly AgentPlace[]): boolean {
  return agents.some((a) => !a.parti && a.activite === "machine");
}
