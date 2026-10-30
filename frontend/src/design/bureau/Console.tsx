const TOUCHES = [4, 6, 8, 10, 12, 14];

/**
 * Le pupitre de console d'un agent de produit, dans la grille 20 × 18 du poste :
 * un écran sombre, une façade de métal et une rangée de touches. Du mobilier
 * fixe, qui ne dit rien de l'état : c'est la pose de l'agent qui le porte.
 * Il se dessine dans le `<svg>` de l'agent, devant lui.
 */
export default function Console() {
  return (
    <g data-sprite="console">
      <rect x="13" y="4" width="6" height="6" className="fill-(--sprite-metal-ombre)" />
      <rect x="14" y="5" width="4" height="4" className="fill-(--sprite-console-ecran)" />
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
