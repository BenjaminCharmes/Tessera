import type { ReactNode } from "react";
import type { EcranId } from "../../lib/bureau/ecranDuPoste";
import { TON_ECRAN } from "./tons";
import type { TonDePoste } from "./tons";

/*
 * Les scènes de l'écran, sur une grille de 6 × 4 pixels (la zone allumée de
 * l'écran fait 6 × 4 unités du poste, une par pixel). Elles ne portent que des teintes d'état
 * (ADR-026), écrites en toutes lettres. Une animation n'est posée que si `anime`
 * est vrai : la scène immobile dit « rien ne bouge », elle ne ment pas (ADR-058).
 */

interface ScenePropos {
  /** Vrai quand l'agent travaille réellement : seule condition pour poser une classe d'animation. */
  anime: boolean;
  /** La santé du run, ou l'état du poste : teinte des traits de la scène. */
  ton: TonDePoste;
}

function Pixel({ x, y, w = 1, h = 1, classe }: { x: number; y: number; w?: number; h?: number; classe: string }) {
  return <rect x={x} y={y} width={w} height={h} className={classe} />;
}

/** Des lignes de code qui défilent : le motif se répète tous les quatre pixels, la boucle ne saute pas. */
function Code({ anime, ton }: ScenePropos) {
  const trait = TON_ECRAN[ton];
  return (
    <g className={anime ? "anim-defile" : undefined}>
      {[0, 4].map((decalage) => (
        <g key={decalage}>
          <Pixel x={0} y={decalage} w={4} classe={trait} />
          <Pixel x={1} y={decalage + 2} w={3} classe={trait} />
        </g>
      ))}
    </g>
  );
}

/** Une page fixe : le codeur lit, il n'écrit pas. Jamais animée. */
function Lecture() {
  return (
    <g>
      <Pixel x={1} y={0} w={4} h={4} classe="fill-zinc-300" />
      <Pixel x={2} y={1} w={2} classe="fill-zinc-600" />
      <Pixel x={2} y={2} w={2} classe="fill-zinc-600" />
    </g>
  );
}

/** Une barre qui avance ; immobile, elle reste à mi-course. */
function Tests({ anime, ton }: ScenePropos) {
  return (
    <g>
      <Pixel x={0} y={1} w={6} h={2} classe="fill-zinc-700" />
      <Pixel x={0} y={1} w={anime ? 6 : 3} h={2} classe={`${TON_ECRAN[ton]}${anime ? " anim-avance" : ""}`} />
    </g>
  );
}

/** Une ligne de balayage sur un fond de lignes ; immobile, elle reste à la deuxième ligne. */
function Audit({ anime, ton }: ScenePropos) {
  return (
    <g>
      <Pixel x={0} y={0} w={6} classe="fill-zinc-700" />
      <Pixel x={0} y={2} w={6} classe="fill-zinc-700" />
      <Pixel x={0} y={anime ? 0 : 1} w={6} classe={`${TON_ECRAN[ton]}${anime ? " anim-balaie" : ""}`} />
    </g>
  );
}

/** Des lignes de diff : ajoutées en vert, retirées en rouge. */
function Diff({ anime }: ScenePropos) {
  return (
    <g className={anime ? "anim-lueur" : undefined}>
      <Pixel x={0} y={0} w={4} classe="fill-green-400" />
      <Pixel x={0} y={1} w={3} classe="fill-red-400" />
      <Pixel x={0} y={2} w={5} classe="fill-green-400" />
      <Pixel x={0} y={3} w={2} classe="fill-red-400" />
    </g>
  );
}

/** Une liste de cases à cocher, une ligne par critère. */
function Criteres({ anime, ton }: ScenePropos) {
  const trait = TON_ECRAN[ton];
  return (
    <g className={anime ? "anim-lueur" : undefined}>
      <Pixel x={0} y={0} classe="fill-zinc-300" />
      <Pixel x={2} y={0} w={3} classe={trait} />
      <Pixel x={0} y={2} classe="fill-zinc-300" />
      <Pixel x={2} y={2} w={4} classe={trait} />
    </g>
  );
}

/** ✓ : un verdict favorable. Le sprite garde son nom, la pièce le cherche. */
function Ok() {
  return (
    <g data-sprite="coche">
      {[[0, 2], [1, 3], [2, 2], [3, 1], [4, 0]].map(([x, y]) => (
        <Pixel key={`${x}-${y}`} x={x ?? 0} y={y ?? 0} classe="fill-green-400" />
      ))}
    </g>
  );
}

/** ✗ : un verdict défavorable. */
function Ko() {
  return (
    <g data-sprite="croix">
      {[[1, 0], [4, 0], [2, 1], [3, 1], [2, 2], [3, 2], [1, 3], [4, 3]].map(([x, y]) => (
        <Pixel key={`${x}-${y}`} x={x ?? 0} y={y ?? 0} classe="fill-red-400" />
      ))}
    </g>
  );
}

/** La scène d'un écran, ou rien pour `allume` et `eteint`, qui n'en ont pas. */
export default function EcranScene({ ecran, ...propos }: ScenePropos & { ecran: EcranId }): ReactNode {
  switch (ecran) {
    case "code":
      return <Code {...propos} />;
    case "lecture":
      return <Lecture />;
    case "tests":
      return <Tests {...propos} />;
    case "audit":
      return <Audit {...propos} />;
    case "diff":
      return <Diff {...propos} />;
    case "criteres":
      return <Criteres {...propos} />;
    case "ok":
      return <Ok />;
    case "ko":
      return <Ko />;
    default:
      return null;
  }
}
