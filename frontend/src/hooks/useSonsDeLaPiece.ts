import { useEffect, useRef } from "react";
import {
  INTERVALLE_ENTRE_SONS_MS,
  OUVERTURE_MUETTE_MS,
  sonsDeLaTransition,
} from "../lib/bureau/sons";
import type { SignauxSonores } from "../lib/bureau/sons";
import { jouerSon } from "../lib/bureau/synthese";
import type { Son } from "../lib/bureau/synthese";

/**
 * Joue le son d'une pièce quand l'un de ses signaux monte — ticket-603.
 *
 * Réglage coupé : rien ne se joue, mais la référence se met à jour, pour que
 * rallumer le son ne rejoue pas ce qui s'est passé entre-temps. Les deux
 * premières secondes après l'ouverture sont muettes, et un son suit l'autre
 * d'au moins une seconde : un événement trop proche est perdu, pas différé.
 */
export function useSonsDeLaPiece(
  signaux: SignauxSonores,
  actif: boolean,
  jouer: (son: Son) => void = jouerSon,
): void {
  const ouverteA = useRef<number | null>(null);
  const avant = useRef<SignauxSonores | null>(null);
  const dernierA = useRef<number | null>(null);
  const { fete, alarme, machine, demarrages } = signaux;

  useEffect(() => {
    const maintenant = Date.now();
    const ouverture = ouverteA.current ?? maintenant;
    ouverteA.current = ouverture;
    const precedent = avant.current;
    avant.current = { fete, alarme, machine, demarrages };
    if (precedent === null || !actif) return;
    if (maintenant - ouverture < OUVERTURE_MUETTE_MS) return;
    const son = sonsDeLaTransition(precedent, { fete, alarme, machine, demarrages })[0];
    if (son === undefined) return;
    if (dernierA.current !== null && maintenant - dernierA.current < INTERVALLE_ENTRE_SONS_MS) return;
    dernierA.current = maintenant;
    jouer(son);
  }, [fete, alarme, machine, demarrages, actif, jouer]);
}
