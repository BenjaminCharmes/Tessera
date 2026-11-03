import { useMaintenant } from "../../hooks/useMaintenant";
import { formater } from "./duree";

/**
 * Depuis combien de temps ce run tourne — ticket-129.
 *
 * Composant à part, et pas un calcul dans la carte : c'est le seul endroit
 * qui se réaffiche à la seconde. Le mettre dans `RunCard` ferait repeindre la
 * carte entière — et la colonne, quand plusieurs runs tournent.
 *
 * L'horloge est celle de `useMaintenant` (ticket-683) : `setState` vit dans le
 * callback de l'intervalle, jamais dans le corps d'un effet (ticket-123).
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
  // Run terminé : l'horloge reste figée.
  const maintenant = useMaintenant(1000, !termineA);

  const reference = termineA ? Date.parse(termineA) : maintenant;
  return <span>{formater(reference - Date.parse(depuis))}</span>;
}
