import { useId } from "react";

const TOUCHES = [4, 6, 8, 10, 12, 14];

/** Les lignes de texte de l'écran allumé : six, dont deux hors champ pour le défilement. */
const LIGNES: readonly [number, number][] = [
  [4.5, 3],
  [5.5, 2],
  [6.5, 3],
  [7.5, 1.5],
  [8.5, 2.5],
  [9.5, 3],
];

interface ConsoleProps {
  /** L'agent travaille : l'écran s'allume et ses lignes défilent. Sinon il reste éteint (ADR-058). */
  allume: boolean;
}

/**
 * Le pupitre de console d'un agent de produit, dans la grille 20 × 18 du poste :
 * un écran sur son pied, une façade de métal et une rangée de touches. Il se
 * dessine dans le `<svg>` de l'agent, devant lui. Seul l'écran porte un état —
 * celui que le produit déclare pour l'agent ; le défilement (`anim-defile`) se
 * coupe sous `prefers-reduced-motion`.
 */
export default function Console({ allume }: ConsoleProps) {
  const clip = useId();
  return (
    <g data-sprite="console" data-allume={allume}>
      <rect x="13" y="3" width="6" height="6" className="fill-(--sprite-metal-ombre)" />
      <rect
        x="14"
        y="4"
        width="4"
        height="4"
        className={allume ? "fill-(--sprite-console-ecran-allume)" : "fill-(--sprite-console-ecran)"}
      />
      {allume && (
        <>
          <clipPath id={clip}>
            <rect x="14" y="4" width="4" height="4" />
          </clipPath>
          <g clipPath={`url(#${clip})`}>
            <g className="anim-defile">
              {LIGNES.map(([y, largeur]) => (
                <rect key={y} x="14.5" y={y} width={largeur} height="0.5" className="fill-(--sprite-console-texte)" />
              ))}
            </g>
          </g>
        </>
      )}
      <rect x="15" y="9" width="2" height="3" className="fill-(--sprite-metal-ombre)" />
      <rect x="14" y="11" width="4" height="1" className="fill-(--sprite-metal)" />
      <rect x="1" y="12" width="18" height="2" className="fill-(--sprite-metal-clair)" />
      <rect x="1" y="14" width="18" height="1" className="fill-(--sprite-metal-ombre)" />
      {TOUCHES.map((x) => (
        <rect key={x} x={x} y="12" width="1" height="1" className="fill-(--sprite-console-touche)" />
      ))}
      <rect x="2" y="15" width="1" height="3" className="fill-(--sprite-metal)" />
      <rect x="17" y="15" width="1" height="3" className="fill-(--sprite-metal)" />
    </g>
  );
}
