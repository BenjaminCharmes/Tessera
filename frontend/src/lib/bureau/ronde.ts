import type { ProjetPourLaColonne } from "./aToi";
import { postesDuRun } from "./postesDuRun";
import type { PosteId } from "./postesDuRun";
import { enEtapeSilencieuse, santeAgent } from "../santeAgent";
import type { SanteAgent } from "../santeAgent";

/** Combien de temps le directeur reste derrière un agent avant de revenir à son bureau. */
export const DUREE_DE_VISITE_MS = 20_000;
/**
 * Le délai minimal entre deux visites dues à la santé. L'horloge du Bureau bat toutes
 * les 5 s : un multiple de 5 s évite qu'une visite démarre un tick trop tôt ou trop tard.
 */
export const ECART_ENTRE_VISITES_MS = 60_000;

/** Où se tient le directeur : derrière l'agent d'un poste, dans la pièce d'un projet. */
export interface Visite {
  projet: string;
  poste: PosteId;
  /** L'instant où il est parti de son bureau. */
  depuis: number;
}

/** Ce que l'utilisateur a demandé : un agent cliqué ou le fil d'une pièce, daté de l'instant du geste. */
export interface DemandeDeVisite {
  projet: string;
  poste: PosteId;
  a: number;
}

/** Ce que la ronde retient d'un tick à l'autre : pas de minuteur, seulement de quoi comparer. */
export interface MemoireDeRonde {
  /** La santé de chaque run vivant au tick précédent : une visite part d'un changement. */
  vues: Readonly<Record<string, SanteAgent>>;
  /** Le départ de la dernière visite due à la santé, pour `ECART_ENTRE_VISITES_MS`. */
  derniereVisiteDeSante: number | null;
  /** La dernière demande de l'utilisateur déjà traitée : elle ne repart pas au tick suivant. */
  demandeVue: number | null;
  visite: Visite | null;
}

export const MEMOIRE_VIERGE: MemoireDeRonde = {
  vues: {},
  derniereVisiteDeSante: null,
  demandeVue: null,
  visite: null,
};

/** Le poste dont l'agent travaille : la seule place où le directeur a quelque chose à voir. */
export function posteOccupe(projet: ProjetPourLaColonne): PosteId | null {
  return postesDuRun(projet.etat).find((p) => p.etat === "occupe")?.poste ?? null;
}

/** La santé des runs vivants : un projet sans run, ou dont le run est clos, n'a rien à montrer. */
function santesDesRuns(
  projets: readonly ProjetPourLaColonne[],
  maintenant: number,
): Record<string, SanteAgent> {
  const santes: Record<string, SanteAgent> = {};
  for (const { nom, etat } of projets) {
    if (etat.ticketEvents.length === 0 || etat.runClosed) continue;
    santes[nom] = santeAgent(
      etat.dernierEvenementA,
      maintenant,
      etat.pendingQuestion,
      etat.attenteExterieure !== null,
      enEtapeSilencieuse(etat),
    );
  }
  return santes;
}

function estSilencieuse(sante: SanteAgent | undefined): boolean {
  return sante === "attente" || sante === "blocage_suspecte";
}

/** Le premier projet qui vient de passer `silencieux` ou `figé ?`, avec son poste occupé. */
function premiereVisiteDeSante(
  projets: readonly ProjetPourLaColonne[],
  avant: MemoireDeRonde["vues"],
  apres: Record<string, SanteAgent>,
  maintenant: number,
): Visite | null {
  for (const projet of projets) {
    const sante = apres[projet.nom];
    if (!estSilencieuse(sante) || avant[projet.nom] === sante) continue;
    const poste = posteOccupe(projet);
    if (poste !== null) return { projet: projet.nom, poste, depuis: maintenant };
  }
  return null;
}

function memoireEgale(a: MemoireDeRonde, b: MemoireDeRonde): boolean {
  const nomsA = Object.keys(a.vues);
  return (
    a.derniereVisiteDeSante === b.derniereVisiteDeSante &&
    a.demandeVue === b.demandeVue &&
    a.visite?.projet === b.visite?.projet &&
    a.visite?.poste === b.visite?.poste &&
    a.visite?.depuis === b.visite?.depuis &&
    nomsA.length === Object.keys(b.vues).length &&
    nomsA.every((nom) => a.vues[nom] === b.vues[nom])
  );
}

/** Une visite encore due : elle dure `DUREE_DE_VISITE_MS`, et sa pièce doit encore exister. */
function visiteEnCours(
  visite: Visite | null,
  projets: readonly ProjetPourLaColonne[],
  maintenant: number,
): Visite | null {
  if (visite === null || maintenant - visite.depuis >= DUREE_DE_VISITE_MS) return null;
  return projets.some((p) => p.nom === visite.projet) ? visite : null;
}

/** La visite que l'utilisateur demande, ou celle qu'un run venu de passer silencieux appelle. */
function choisirLaVisite(
  base: MemoireDeRonde,
  memoire: MemoireDeRonde,
  projets: readonly ProjetPourLaColonne[],
  demande: DemandeDeVisite | null,
  maintenant: number,
): MemoireDeRonde {
  if (demande !== null && demande.a !== memoire.demandeVue && projets.some((p) => p.nom === demande.projet)) {
    return { ...base, visite: { projet: demande.projet, poste: demande.poste, depuis: maintenant } };
  }
  const ecartPasse =
    memoire.derniereVisiteDeSante === null ||
    maintenant - memoire.derniereVisiteDeSante >= ECART_ENTRE_VISITES_MS;
  if (base.visite !== null || !ecartPasse) return base;
  const visite = premiereVisiteDeSante(projets, memoire.vues, base.vues, maintenant);
  return visite === null ? base : { ...base, visite, derniereVisiteDeSante: maintenant };
}

/**
 * La ronde du directeur, pure : la visite en cours et la mémoire du tick suivant.
 * Chaque départ dit un fait (ADR-058) : un run qui vient de passer `silencieux` ou
 * `figé ?`, ou un agent que l'utilisateur a choisi — celui-ci passe avant le délai
 * `ECART_ENTRE_VISITES_MS` et remplace une visite en cours. Une question en attente
 * (ADR-025) retient le directeur à son bureau et arrête la visite. Un run silencieux
 * pendant le délai est ignoré, pas différé. Rendre la même mémoire quand rien ne
 * change permet de la relire à chaque rendu sans boucler.
 */
export function ronde(
  memoire: MemoireDeRonde,
  projets: readonly ProjetPourLaColonne[],
  demande: DemandeDeVisite | null,
  maintenant: number,
): MemoireDeRonde {
  const base: MemoireDeRonde = {
    vues: santesDesRuns(projets, maintenant),
    derniereVisiteDeSante: memoire.derniereVisiteDeSante,
    demandeVue: demande?.a ?? memoire.demandeVue,
    visite: visiteEnCours(memoire.visite, projets, maintenant),
  };
  const enQuestion = projets.some((p) => p.etat.pendingQuestion !== null);
  const suivante = enQuestion
    ? { ...base, visite: null }
    : choisirLaVisite(base, memoire, projets, demande, maintenant);
  return memoireEgale(memoire, suivante) ? memoire : suivante;
}
