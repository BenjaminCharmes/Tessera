import { useCallback, useEffect, useState } from "react";
import {
  ajouter,
  ecrireHistorique,
  lireHistorique,
  nonLus,
  toutMarquerLu,
  type EntreeHistorique,
} from "../lib/historiqueNotifications";
import type { Notif } from "../lib/notifications";

/**
 * L'historique du jour de la cloche, en état React — ticket-554.
 *
 * Relu et purgé au chargement (`lireHistorique`), réécrit à chaque changement.
 * La logique est dans `lib/historiqueNotifications` ; ce hook ne fait que la
 * brancher sur le stockage.
 */
export function useHistoriqueNotifications(): {
  historique: EntreeHistorique[];
  nonLus: number;
  enregistrer: (notifs: Notif[]) => void;
  toutMarquerLu: () => void;
} {
  const [etat, setEtat] = useState(() => lireHistorique(new Date()));

  useEffect(() => {
    ecrireHistorique(etat);
  }, [etat]);

  const enregistrer = useCallback((notifs: Notif[]) => {
    setEtat((h) => ajouter(h, notifs, new Date()));
  }, []);
  const marquerToutLu = useCallback(() => setEtat(toutMarquerLu), []);

  return {
    historique: etat.items,
    nonLus: nonLus(etat),
    enregistrer,
    toutMarquerLu: marquerToutLu,
  };
}
