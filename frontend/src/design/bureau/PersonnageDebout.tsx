import type { Physique, Tenue } from "../../lib/bureau/physique";
import Tete from "./Tete";
import { FILL_HAUT, FILL_OMBRE, FILL_PEAU } from "./tons";

interface PersonnageDeboutProps {
  tenue: Tenue;
  physique: Physique;
  /** Les bras levés, sans tasse : l'agent fête la PR mergée. */
  brasLeves?: boolean;
  /** Les bras le long du corps, mains vides : l'agent fait une pause. */
  sansTasse?: boolean;
  /** Une feuille annotée à la main, à la place de la tasse : l'agent rend sa copie. */
  feuille?: boolean;
}

/** Le bras tendu qui porte la feuille : papier clair, deux lignes d'annotation. */
function BrasALaFeuille({ ombre }: { ombre: string }) {
  return (
    <g data-detail="feuille">
      <rect x="0" y="7" width="1" height="5" className={ombre} />
      <rect x="9" y="6" width="1" height="4" className={ombre} />
      <rect x="10" y="3" width="3" height="5" className="fill-(--sprite-feuille)" />
      <rect x="10" y="4" width="2" height="1" className="fill-(--sprite-feuille-annotation)" />
      <rect x="10" y="6" width="2" height="1" className="fill-(--sprite-feuille-annotation)" />
    </g>
  );
}

/** Les bras : le long du corps et la tasse à la main, levés au-dessus de la tête, ou tendus avec la feuille. */
function Bras({
  haut,
  brasLeves,
  sansTasse,
  feuille,
}: {
  haut: Tenue["haut"];
  brasLeves: boolean;
  sansTasse: boolean;
  feuille: boolean;
}) {
  const ombre = FILL_OMBRE[haut];
  if (feuille) return <BrasALaFeuille ombre={ombre} />;
  if (brasLeves) {
    return (
      <g data-bras="leves">
        <rect x="0" y="0" width="1" height="7" className={ombre} />
        <rect x="9" y="0" width="1" height="7" className={ombre} />
      </g>
    );
  }
  if (sansTasse) {
    return (
      <g data-bras="ballants">
        <rect x="0" y="7" width="1" height="5" className={ombre} />
        <rect x="9" y="7" width="1" height="5" className={ombre} />
      </g>
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
 * tasse à la main, les mains vides en pause, ou les bras levés pour fêter la PR. Il se dessine à côté de
 * son poste, pas dedans.
 */
export default function PersonnageDebout({
  tenue,
  physique,
  brasLeves = false,
  sansTasse = false,
  feuille = false,
}: PersonnageDeboutProps) {
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
      <Bras haut={tenue.haut} brasLeves={brasLeves} sansTasse={sansTasse} feuille={feuille} />
    </g>
  );
}
