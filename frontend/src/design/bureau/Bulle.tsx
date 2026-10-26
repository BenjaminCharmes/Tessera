import type { SanteAgent } from "../../lib/santeAgent";
import { SIGNE_BULLE, TON_BULLE } from "./tons";

interface BulleProps {
  sante: SanteAgent;
}

/**
 * La bulle au-dessus d'un poste occupé : un signe, jamais le mot — la pastille
 * du pied de la pièce l'écrit déjà. Un agent qui travaille n'en a pas.
 * Masquée aux lecteurs d'écran, car le bouton du poste dit déjà l'état.
 */
export default function Bulle({ sante }: BulleProps) {
  const signe = SIGNE_BULLE[sante];
  if (signe === null) return null;
  return (
    <span
      data-testid="bulle"
      aria-hidden="true"
      className={`anim-flotte inline-block rounded-full px-1.5 text-mini font-medium ${TON_BULLE[sante]}`}
    >
      {signe}
    </span>
  );
}
