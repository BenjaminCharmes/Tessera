/**
 * Ce à quoi la socket d'observation doit être abonnée — ticket-183.
 *
 * ADR-041 ne pousse le texte d'un run qu'aux clients qui l'ont demandé. Le
 * serveur tient un **ensemble** par socket ; le client le réduisait à une
 * seule valeur, que deux consommateurs se disputaient — le panneau du projet
 * actif et la sélection de l'onglet Supervision. Un slot pour deux besoins :
 * celui qui ne parlait pas perdait son texte.
 *
 * Les slots sont donc nommés, et l'ensemble voulu s'en déduit. Un run demandé
 * par les deux ne s'abonne qu'une fois et ne se désabonne que lorsque plus
 * personne ne le regarde.
 */

/** Les consommateurs d'un abonnement, chacun tenant au plus un run. */
export interface SlotsDAbonnement {
  /** Le run choisi dans l'onglet Supervision. */
  selection: string | null;
  /** Le run que le panneau du projet actif affiche. */
  panneau: string | null;
}

export interface DiffDAbonnements {
  ajouts: string[];
  retraits: string[];
}

/** L'ensemble voulu, sans doublon ni valeur vide. */
export function abonnementsVoulus(slots: SlotsDAbonnement): Set<string> {
  const voulus = new Set<string>();
  if (slots.selection) voulus.add(slots.selection);
  if (slots.panneau) voulus.add(slots.panneau);
  return voulus;
}

/**
 * Ce qu'il reste à envoyer pour passer d'un état à l'autre.
 *
 * Rendre le diff plutôt que l'ensemble voulu évite de renvoyer un `subscribe`
 * déjà en vigueur à chaque changement de slot — le serveur l'accepterait, mais
 * la socket porterait un bavardage qui n'apprend rien.
 */
export function diffDesAbonnements(
  actuels: ReadonlySet<string>,
  voulus: ReadonlySet<string>,
): DiffDAbonnements {
  return {
    ajouts: [...voulus].filter((run) => !actuels.has(run)),
    retraits: [...actuels].filter((run) => !voulus.has(run)),
  };
}
