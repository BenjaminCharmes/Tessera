/** Trois espèces : la plante en pot, le cactus et le ficus, plus haut, qui se pose contre un mur. */
export type EspeceDePlante = "pot" | "cactus" | "ficus";

interface PlanteProps {
  espece?: EspeceDePlante;
}

/** La plante en pot, grille 8 × 10. */
function EnPot() {
  return (
    <>
      <rect x="1" y="2" width="2" height="2" className="fill-(--sprite-plante)" />
      <rect x="5" y="1" width="2" height="3" className="fill-(--sprite-plante)" />
      <rect x="3" y="0" width="2" height="5" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="4" width="4" height="1" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="5" width="4" height="1" className="fill-(--sprite-pot)" />
      <rect x="2" y="6" width="4" height="4" className="fill-(--sprite-pot)" />
    </>
  );
}

/** Le cactus, grille 8 × 10 : un tronc, deux bras, un pot clair. */
function Cactus() {
  return (
    <>
      <rect x="3" y="0" width="2" height="6" className="fill-(--sprite-cactus)" />
      <rect x="1" y="2" width="1" height="2" className="fill-(--sprite-cactus)" />
      <rect x="1" y="3" width="2" height="1" className="fill-(--sprite-cactus)" />
      <rect x="6" y="1" width="1" height="3" className="fill-(--sprite-cactus)" />
      <rect x="5" y="3" width="2" height="1" className="fill-(--sprite-cactus)" />
      <rect x="2" y="6" width="4" height="4" className="fill-(--sprite-pot-clair)" />
    </>
  );
}

/** Le ficus, grille 8 × 16 : un feuillage en boule sur un tronc fin. */
function Ficus() {
  return (
    <>
      <rect x="1" y="1" width="6" height="5" className="fill-(--sprite-plante)" />
      <rect x="2" y="0" width="4" height="1" className="fill-(--sprite-plante)" />
      <rect x="0" y="3" width="1" height="2" className="fill-(--sprite-plante-ombre)" />
      <rect x="7" y="2" width="1" height="3" className="fill-(--sprite-plante-ombre)" />
      <rect x="2" y="4" width="2" height="2" className="fill-(--sprite-plante-ombre)" />
      <rect x="3" y="6" width="1" height="5" className="fill-(--sprite-pot)" />
      <rect x="2" y="11" width="4" height="5" className="fill-(--sprite-pot)" />
    </>
  );
}

/** Une plante, posée dans un coin de pièce ou de salle : du mobilier fixe (ADR-058). */
export default function Plante({ espece = "pot" }: PlanteProps) {
  const haute = espece === "ficus";
  return (
    <svg
      width="40"
      height={haute ? 80 : 50}
      viewBox={haute ? "0 0 8 16" : "0 0 8 10"}
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="plante"
      data-espece={espece}
    >
      {espece === "cactus" ? <Cactus /> : haute ? <Ficus /> : <EnPot />}
    </svg>
  );
}
