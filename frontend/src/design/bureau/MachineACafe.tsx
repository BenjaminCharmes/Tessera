import { machineACafe, meubleBas } from "../../lib/bureau/sprites/mobilier";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

const machine = memoise(machineACafe);
const meuble = memoise(meubleBas);

/** La hauteur du meuble bas, en px : la machine se pose dessus. */
export const HAUTEUR_DU_MEUBLE_BAS = 24;

/**
 * La machine à café sur son meuble bas (ticket-727) : afficheur, boutons, tasse pleine,
 * à hauteur de main d'un agent debout. Aucun voyant : rien ne dit qu'on s'en sert
 * (ADR-058) ; la vapeur se pose à part, quand un agent est à la machine.
 */
export default function MachineACafe() {
  return (
    <span aria-hidden="true" className="flex flex-col items-center" data-sprite="machine-a-cafe">
      {/* La machine à 80 % de l'échelle du meuble, comme dans l'atelier. */}
      <SpriteSvg sprite={machine()} largeur={28.8} hauteur={38.4} />
      <SpriteSvg sprite={meuble()} largeur={48} hauteur={HAUTEUR_DU_MEUBLE_BAS} data-sprite="meuble-bas" />
    </span>
  );
}
