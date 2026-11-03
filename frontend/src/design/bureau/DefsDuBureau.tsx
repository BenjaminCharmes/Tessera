import { memo, useSyncExternalStore } from "react";
import { type ContenuDuSymbole, abonner, symbolesInscrits } from "../../lib/bureau/sprites/symboles";

function Chemins({ contenu }: { contenu: ContenuDuSymbole }) {
  return contenu.chemins.map(({ d, fill, opacity }, i) => (
    <path key={i} d={d} style={opacity === undefined ? { fill } : { fill, opacity }} />
  ));
}

/** Un symbole, ou un motif de tuile : son contenu ne change jamais, son empreinte en est l'identité. */
const Symbole = memo(function Symbole({ contenu }: { contenu: ContenuDuSymbole }) {
  const viewBox = `0 0 ${contenu.w} ${contenu.h}`;
  if (contenu.tuile)
    return (
      <pattern
        id={contenu.id}
        patternUnits="userSpaceOnUse"
        width={contenu.tuile.largeur}
        height={contenu.tuile.hauteur}
        viewBox={viewBox}
        preserveAspectRatio="none"
      >
        <Chemins contenu={contenu} />
      </pattern>
    );
  return (
    <symbol id={contenu.id} viewBox={viewBox} overflow="visible">
      <Chemins contenu={contenu} />
    </symbol>
  );
});

/**
 * Le `<defs>` commun des sprites du Bureau (ticket-727) : chaque calque dessiné
 * une fois, quel que soit le nombre de pièces qui le posent. Il ne porte que ce
 * qu'un sprite monté a inscrit : hors du Bureau, il est vide. Monté une fois, à
 * la racine de l'app. Un motif de nuit se déclare sous `data-moment="nuit"` : la
 * couleur d'un `<pattern>` se résout là où il est déclaré.
 */
export default function DefsDuBureau() {
  const symboles = useSyncExternalStore(abonner, symbolesInscrits);
  const nuit = symboles.filter((s) => s.tuile?.moment === "nuit");
  return (
    <svg
      aria-hidden="true"
      width="0"
      height="0"
      shapeRendering="crispEdges"
      className="pointer-events-none absolute"
      data-defs="bureau"
    >
      <defs>
        {symboles
          .filter((s) => s.tuile?.moment !== "nuit")
          .map((s) => (
            <Symbole key={s.id} contenu={s} />
          ))}
      </defs>
      <g data-moment="nuit">
        <defs>
          {nuit.map((s) => (
            <Symbole key={s.id} contenu={s} />
          ))}
        </defs>
      </g>
    </svg>
  );
}
