import { useEffect, useState } from "react";

/**
 * `Date.now()` rafraîchi à intervalle fixe, pour qu'un affichage change sans nouvel événement.
 *
 * `actif` à `false` fige la valeur : un run clos n'a plus besoin de battre.
 */
export function useMaintenant(intervalleMs = 5_000, actif = true): number {
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    if (!actif) return;
    const id = setInterval(() => setMaintenant(Date.now()), intervalleMs);
    return () => clearInterval(id);
  }, [intervalleMs, actif]);

  return maintenant;
}
