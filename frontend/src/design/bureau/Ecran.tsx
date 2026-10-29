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

/**
 * L'écran posé sur le bureau, dans la grille 20 × 18 du poste. Sa zone allumée fait
 * 6 × 4 unités, la taille de la scène : à 3 × 2, elle était rendue à moitié, illisible.
 */
export default function Ecran({ ecran, ton, anime }: EcranProps) {
  const sansScene = ecran === "allume" || ecran === "eteint";
  return (
    <g data-sprite="ecran" data-ecran={ecran}>
      <rect x="12" y="5" width="8" height="6" className="fill-zinc-800" />
      {sansScene ? (
        <rect
          x="13"
          y="6"
          width="6"
          height="4"
          className={`${TON_ECRAN[ton]}${anime ? " anim-lueur" : ""}`}
        />
      ) : (
        <>
          <rect x="13" y="6" width="6" height="4" className="fill-zinc-900" />
          {/* Un `<svg>` imbriqué rogne ce qui défile : la scène reste sur sa zone allumée. */}
          <svg x="13" y="6" width="6" height="4" viewBox="0 0 6 4" className="overflow-hidden">
            <EcranScene ecran={ecran} anime={anime} ton={ton} />
          </svg>
        </>
      )}
      <rect x="15" y="11" width="2" height="1" className="fill-zinc-800" />
    </g>
  );
}
