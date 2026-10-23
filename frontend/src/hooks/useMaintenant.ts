import { useEffect, useState } from "react";

/** `Date.now()` rafraîchi à intervalle fixe, pour qu'un affichage change sans nouvel événement. */
export function useMaintenant(intervalleMs = 5_000): number {
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setMaintenant(Date.now()), intervalleMs);
    return () => clearInterval(id);
  }, [intervalleMs]);

  return maintenant;
}
