import { LIBELLE_SANTE } from "../../lib/santeAgent";
import type { SanteAgent } from "../../lib/santeAgent";
import { TON_BULLE } from "./tons";

interface BulleProps {
  sante: SanteAgent;
}

/**
 * La bulle au-dessus d'un poste occupé : le libellé de santé, et rien d'autre.
 * Masquée aux lecteurs d'écran, car le bouton du poste dit déjà l'état.
 */
export default function Bulle({ sante }: BulleProps) {
  return (
    <span
      data-testid="bulle"
      aria-hidden="true"
      className={`anim-flotte inline-block rounded-full px-1.5 text-mini font-medium ${TON_BULLE[sante]}`}
    >
      {LIBELLE_SANTE[sante]}
    </span>
  );
}
