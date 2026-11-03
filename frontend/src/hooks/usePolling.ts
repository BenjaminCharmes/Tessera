import { useEffect, useRef } from "react";
import { useFenetreVisible } from "./useFenetreVisible";

export interface OptionsPolling {
  /**
   * Cadence en millisecondes ; `null` suspend le polling. C'est le moyen de
   * déclarer « seulement tant que… » : rien en cours, rien à relire.
   */
  cadenceMs: number | null;
  /**
   * Appelle aussi le rappel dès que le polling (re)démarre : au montage, au
   * retour de la fenêtre, quand la cadence ou `relance` change.
   */
  immediat?: boolean;
  /** Une valeur dont le changement redémarre le polling (nouveau projet, par exemple). */
  relance?: string | number;
}

/**
 * Appelle `rappel` à cadence fixe tant que la fenêtre est visible — ticket-683.
 *
 * Ce que les cinq boucles de lecture périodique réécrivaient chacune
 * (`usePrStatuses`, `useRestants`, `useServices`, `useTickets`,
 * `useAppsEnCours`) :
 *
 * | besoin                    | PR | restants | services | tickets | apps |
 * |---------------------------|----|----------|----------|---------|------|
 * | cadence fixe ou variable  | 30 s | 30 s   | 5 s      | 30/60 s | 10/2 s |
 * | suspendu fenêtre cachée   | oui | oui     | oui      | oui     | oui  |
 * | seulement sous condition  | oui | oui     | oui      | oui     | non  |
 * | appel immédiat + relance  | oui | non     | non      | non     | non  |
 * | arrêt depuis le rappel    | oui | non     | non      | non     | non  |
 * | `clearInterval` au nettoyage | oui | oui  | oui      | oui     | oui  |
 *
 * Ce hook couvre l'union : cadence nullable, visibilité, `immediat` et
 * `relance`. L'arrêt depuis le rappel se dit par un état qui passe la cadence
 * à `null`. Le rappel est lu au tick : changer son identité ne redémarre pas
 * le minuteur. L'annulation d'une réponse en vol reste à l'appelant, qui est
 * seul à connaître sa requête.
 */
export function usePolling(
  rappel: () => void,
  { cadenceMs, immediat = false, relance }: OptionsPolling,
): void {
  const fenetreVisible = useFenetreVisible();
  const rappelRef = useRef(rappel);

  // Déclaré avant l'effet du minuteur : React exécute les effets dans l'ordre.
  useEffect(() => {
    rappelRef.current = rappel;
  }, [rappel]);

  useEffect(() => {
    if (cadenceMs === null || !fenetreVisible) return;
    if (immediat) rappelRef.current();
    const minuteur = setInterval(() => rappelRef.current(), cadenceMs);
    return () => clearInterval(minuteur);
  }, [cadenceMs, fenetreVisible, immediat, relance]);
}
