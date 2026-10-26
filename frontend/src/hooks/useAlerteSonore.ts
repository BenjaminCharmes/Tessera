import { useEffect, useRef } from "react";
import { jouerBip } from "../lib/bureau/bip";

/**
 * Sonne quand une question apparaît — ticket-566.
 *
 * `cles` désigne les projets dont une question attend. Une clé qui n'y était
 * pas au rendu précédent est une question qui passe de `null` à une valeur : on
 * sonne. La première lecture sert de référence et ne sonne jamais : une vue qui
 * s'ouvre sur une question déjà posée ne la « reçoit » pas.
 *
 * Le réglage coupé n'empêche pas la mise à jour de la référence : le rallumer
 * ne doit pas rejouer les questions d'avant.
 */
export function useAlerteSonore(
  cles: readonly string[],
  sonActif: boolean,
  jouer: () => void = jouerBip,
): void {
  const vues = useRef<ReadonlySet<string> | null>(null);
  const signature = cles.join("\u0000");

  useEffect(() => {
    const courantes = new Set(signature === "" ? [] : signature.split("\u0000"));
    const avant = vues.current;
    vues.current = courantes;
    if (avant === null || !sonActif) return;
    if ([...courantes].some((cle) => !avant.has(cle))) jouer();
  }, [signature, sonActif, jouer]);
}
