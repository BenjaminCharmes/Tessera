import { TON_ECRAN } from "./tons";
import type { TonDePoste } from "./tons";

interface EcranProps {
  ton: TonDePoste;
  /** L'écran respire : vrai quand l'agent travaille. */
  lueur: boolean;
}

/** L'écran posé sur le bureau, dans la grille 16 × 18 du poste. */
export default function Ecran({ ton, lueur }: EcranProps) {
  return (
    <g data-sprite="ecran">
      <rect x="10" y="7" width="5" height="4" className="fill-zinc-800" />
      <rect
        x="11"
        y="8"
        width="3"
        height="2"
        className={`${TON_ECRAN[ton]}${lueur ? " anim-lueur" : ""}`}
      />
      <rect x="12" y="11" width="1" height="1" className="fill-zinc-800" />
    </g>
  );
}
