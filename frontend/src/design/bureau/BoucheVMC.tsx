import { boucheVmc } from "../../lib/bureau/sprites/serveurs";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

/** Le régime du ventilateur : arrêté, ou plus rapide quand le projet consomme plus. */
export type RegimeVMC = "arret" | "lent" | "moyen" | "rapide";

/** La durée d'un quart de tour de l'hélice, par régime. */
const DUREE: Record<RegimeVMC, string | null> = {
  arret: null,
  lent: "2.4s",
  moyen: "1.2s",
  rapide: "0.6s",
};

interface BoucheVMCProps {
  regime: RegimeVMC;
}

const dessin = memoise((regime: RegimeVMC) => boucheVmc(DUREE[regime]));

/**
 * La bouche de ventilation, grille 28 × 28 (ticket-727) : cadre vissé, carter rond,
 * hélice à pales courbes derrière sa grille. Le cadre est du mobilier ; l'hélice rend
 * une donnée (ADR-058) : elle ne tourne que si un service du projet tourne, d'autant
 * plus vite que le projet consomme de mémoire. `prefers-reduced-motion` l'arrête.
 */
export default function BoucheVMC({ regime }: BoucheVMCProps) {
  return <SpriteSvg sprite={dessin(regime)} largeur={42} hauteur={42} data-sprite="bouche-vmc" data-regime={regime} />;
}
