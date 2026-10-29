import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import EcranScene from "./EcranScenes";
import { TON_ECRAN } from "./tons";
import type { TonDePoste } from "./tons";

interface EcranProps {
  /** Ce que l'écran montre : une scène d'étape, ✓ ou ✗, ou le simple pixel allumé. */
  ecran: EcranId;
  ton: TonDePoste;
  /** L'écran s'anime : vrai quand l'agent travaille et que le run est actif, jamais sinon. */
  anime: boolean;
}

/** L'écran posé sur le bureau, dans la grille 16 × 18 du poste. */
export default function Ecran({ ecran, ton, anime }: EcranProps) {
  const sansScene = ecran === "allume" || ecran === "eteint";
  return (
    <g data-sprite="ecran" data-ecran={ecran}>
      <rect x="10" y="7" width="5" height="4" className="fill-zinc-800" />
      {sansScene ? (
        <rect
          x="11"
          y="8"
          width="3"
          height="2"
          className={`${TON_ECRAN[ton]}${anime ? " anim-lueur" : ""}`}
        />
      ) : (
        <>
          <rect x="11" y="8" width="3" height="2" className="fill-zinc-900" />
          {/* Un `<svg>` imbriqué rogne ce qui défile : la scène reste sur sa zone allumée. */}
          <svg x="11" y="8" width="3" height="2" viewBox="0 0 6 4" className="overflow-hidden">
            <EcranScene ecran={ecran} anime={anime} ton={ton} />
          </svg>
        </>
      )}
      <rect x="12" y="11" width="1" height="1" className="fill-zinc-800" />
    </g>
  );
}
