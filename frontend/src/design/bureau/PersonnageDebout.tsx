import type { Physique, Tenue } from "../../lib/bureau/physique";
import Tete from "./Tete";
import { FILL_HAUT, FILL_OMBRE, FILL_PEAU } from "./tons";

interface PersonnageDeboutProps {
  tenue: Tenue;
  physique: Physique;
  /** Les bras levés, sans tasse : l'agent s'étire. */
  etire?: boolean;
}

/** Les bras : le long du corps et la tasse à la main, ou levés au-dessus de la tête. */
function Bras({ haut, etire }: { haut: Tenue["haut"]; etire: boolean }) {
  const ombre = FILL_OMBRE[haut];
  if (etire) {
    return (
      <>
        <rect x="0" y="0" width="1" height="7" className={ombre} />
        <rect x="9" y="0" width="1" height="7" className={ombre} />
      </>
    );
  }
  return (
    <>
      <rect x="0" y="7" width="1" height="5" className={ombre} />
      <rect x="9" y="7" width="1" height="3" className={ombre} />
      <rect x="10" y="6" width="2" height="2" className="fill-zinc-200" />
    </>
  );
}

/** Les jambes : jupe et mollets nus, ou pantalon. */
function Jambes({ tenue, physique }: PersonnageDeboutProps) {
  if (!physique.jupe) {
    return (
      <>
        <rect x="2" y="13" width="2" height="7" className="fill-zinc-700" />
        <rect x="6" y="13" width="2" height="7" className="fill-zinc-700" />
      </>
    );
  }
  const peau = FILL_PEAU[physique.peau];
  return (
    <>
      <rect x="1" y="13" width="8" height="3" className={FILL_OMBRE[tenue.haut]} />
      <rect x="3" y="16" width="1" height="4" className={peau} />
      <rect x="6" y="16" width="1" height="4" className={peau} />
    </>
  );
}

/**
 * Le personnage debout, dans la grille 12 × 20 (42 × 70 px) : l'agent qui a fini,
 * tasse à la main, ou les bras levés quand il s'étire. Il se dessine à côté de
 * son poste, pas dedans.
 */
export default function PersonnageDebout({ tenue, physique, etire = false }: PersonnageDeboutProps) {
  const ombre = FILL_OMBRE[tenue.haut];
  return (
    <g data-sprite="personnage" data-pose="debout">
      <Tete physique={physique} x={2} y={2} />
      <rect x="1" y="6" width="8" height="7" className={FILL_HAUT[tenue.haut]} />
      {tenue.cravate && (
        <g data-detail="cravate">
          <rect x="4" y="6" width="2" height="1" className="fill-(--sprite-col)" />
          <rect x="4" y="7" width="2" height="4" className="fill-(--sprite-cravate)" />
        </g>
      )}
      {tenue.capuche && <rect data-detail="capuche" x="3" y="6" width="4" height="1" className={ombre} />}
      <Jambes tenue={tenue} physique={physique} />
      <Bras haut={tenue.haut} etire={etire} />
    </g>
  );
}
