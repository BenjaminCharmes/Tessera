import { useEffect, useState } from "react";
import { formater } from "./duree";

/**
 * Depuis combien de temps ce run tourne — ticket-129.
 *
 * Composant à part, et pas un calcul dans la carte : c'est le seul endroit
 * qui se réaffiche à la seconde. Le mettre dans `RunCard` ferait repeindre la
 * carte entière — et la colonne, quand plusieurs runs tournent.
 *
 * `setState` vit dans le callback de l'intervalle, jamais dans le corps de
 * l'effet : c'est exactement le motif des dix-neuf erreurs
 * `react-hooks/set-state-in-effect` corrigées par ticket-123.
 *
 * `termineA` fige l'affichage à l'heure de clôture du run (ticket-279) :
 * le chrono s'arrête dès que le run est fermé.
 */
export default function Chrono({
  depuis,
  termineA,
}: {
  depuis: string;
  termineA?: string;
}) {
  const [maintenant, setMaintenant] = useState(() => Date.now());

  useEffect(() => {
    if (termineA) return; // Run terminé : l'horloge reste figée.
    const t = setInterval(() => setMaintenant(Date.now()), 1000);
    return () => clearInterval(t);
  }, [termineA]);

  const reference = termineA ? Date.parse(termineA) : maintenant;
  return <span>{formater(reference - Date.parse(depuis))}</span>;
}
