import { useEffect, useState } from "react";
import { libelleDeLAttente, resteAvant } from "./attente";

/**
 * Le temps qui reste avant qu'un agent reprenne seul — ticket-186.
 *
 * Composant à part, comme `Chrono` : c'est le seul endroit qui se réaffiche à
 * la seconde, et le mettre dans le panneau ferait repeindre tout le reste.
 *
 * `setState` vit dans le callback de l'intervalle, jamais dans le corps de
 * l'effet (ticket-123).
 */
export default function CompteARebours({ expireA }: { expireA: string | null }) {
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    // Pas d'échéance, pas d'horloge : le composant rend `null`, et un
    // intervalle qui bat pour rien réveille chaque carte à la seconde.
    if (!expireA) return;
    const echeance = Date.parse(expireA);
    if (Number.isNaN(echeance)) return;

    const t = setInterval(() => {
      setMaintenant(Date.now());
      // Le délai est passé : le libellé ne changera plus.
      if (Date.now() >= echeance) clearInterval(t);
    }, 1000);
    return () => clearInterval(t);
  }, [expireA]);

  const libelle = libelleDeLAttente(resteAvant(expireA, maintenant));
  if (!libelle) return null;

  // Un `span` en bloc, et non un `p` : la carte de Supervision est un
  // `button` fait de `span`, qui n'accepte pas de contenu de flux.
  return (
    <span className="mt-1 block text-micro text-amber-600">{libelle}</span>
  );
}
