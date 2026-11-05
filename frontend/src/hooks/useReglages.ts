import { useCallback, useEffect, useState } from "react";
import { reglages as api, texteDeLErreur, type Reglage } from "../lib/apiReglages";

interface EtatDesReglages {
  liste: Reglage[];
  /** Vrai tant que la première lecture n'est pas revenue. */
  chargement: boolean;
  /** L'échec de la lecture, en texte. */
  erreur: string | null;
  /** Pose une valeur puis relit ; rend le texte de l'erreur, ou null si tout va bien. */
  ecrire: (nom: string, valeur: number | boolean) => Promise<string | null>;
  /** Rend un réglage à son défaut puis relit ; même retour que `ecrire`. */
  retirer: (nom: string) => Promise<string | null>;
}

/** Les réglages globaux (ADR-075) : lecture, écriture, retour au défaut. */
export function useReglages(): EtatDesReglages {
  const [liste, setListe] = useState<Reglage[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  const relire = useCallback(async () => {
    try {
      setListe(await api.list());
      setErreur(null);
    } catch (e) {
      setErreur(texteDeLErreur(e));
    } finally {
      setChargement(false);
    }
  }, []);

  // Première lecture : inline, pour qu'aucun `setState` ne parte de façon synchrone.
  useEffect(() => {
    let actif = true;
    api
      .list()
      .then((lues) => {
        if (actif) setListe(lues);
      })
      .catch((e: unknown) => {
        if (actif) setErreur(texteDeLErreur(e));
      })
      .finally(() => {
        if (actif) setChargement(false);
      });
    return () => {
      actif = false;
    };
  }, []);

  const appliquer = useCallback(
    async (action: () => Promise<Reglage>): Promise<string | null> => {
      try {
        await action();
      } catch (e) {
        return texteDeLErreur(e);
      }
      await relire();
      return null;
    },
    [relire],
  );

  const ecrire = useCallback(
    (nom: string, valeur: number | boolean) => appliquer(() => api.ecrire(nom, valeur)),
    [appliquer],
  );
  const retirer = useCallback((nom: string) => appliquer(() => api.retirer(nom)), [appliquer]);

  return { liste, chargement, erreur, ecrire, retirer };
}
