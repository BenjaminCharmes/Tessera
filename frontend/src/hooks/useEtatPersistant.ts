import { useEffect, useState } from "react";

/**
 * Un `useState` qui survit au rechargement — ticket-193.
 *
 * Réservé aux commodités par onglet : projet actif, panneau ouvert, onglet
 * de droite. Jamais à l'état d'un run ni au texte des agents : le backend
 * les tient (tickets 183, 185), et deux sources divergeraient.
 *
 * `localStorage` peut être vide, bloqué ou lever — mode privé, stockage
 * refusé — : chaque accès est enveloppé, et le défaut sert alors. `valide`
 * écarte une valeur mémorisée par une version précédente de l'IDE qui ne
 * voudrait plus rien dire.
 */
const PREFIXE = "tessera.ui.";

export function lireEtatPersistant<T>(
  cle: string,
  defaut: T,
  valide?: (v: unknown) => v is T,
): T {
  try {
    const brut = window.localStorage.getItem(PREFIXE + cle);
    if (brut === null) return defaut;
    const valeur: unknown = JSON.parse(brut);
    if (valide && !valide(valeur)) return defaut;
    return valeur as T;
  } catch {
    return defaut;
  }
}

export function useEtatPersistant<T>(
  cle: string,
  defaut: T,
  valide?: (v: unknown) => v is T,
): [T, (v: T | ((prev: T) => T)) => void] {
  const [valeur, setValeur] = useState<T>(() =>
    lireEtatPersistant(cle, defaut, valide),
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(PREFIXE + cle, JSON.stringify(valeur));
    } catch {
      // Stockage indisponible : l'état vit le temps de l'onglet, comme avant.
    }
  }, [cle, valeur]);

  return [valeur, setValeur];
}

/** Un garde pour une union de chaînes. */
export function parmi<T extends string>(valeurs: readonly T[]) {
  return (v: unknown): v is T =>
    typeof v === "string" && (valeurs as readonly string[]).includes(v);
}
