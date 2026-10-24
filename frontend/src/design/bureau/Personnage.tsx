interface PersonnageProps {
  /** Les mains tapent : vrai quand l'agent travaille. */
  tape: boolean;
}

/** Le personnage assis à un poste occupé, dans la grille 16 × 18 du poste. */
export default function Personnage({ tape }: PersonnageProps) {
  return (
    <g data-sprite="personnage">
      <rect x="5" y="1" width="6" height="2" className="fill-(--sprite-cheveux)" />
      <rect x="5" y="3" width="6" height="4" className="fill-(--sprite-peau)" />
      <rect x="6" y="4" width="1" height="1" className="fill-zinc-900" />
      <rect x="9" y="4" width="1" height="1" className="fill-zinc-900" />
      <rect x="4" y="7" width="8" height="5" className="fill-(--sprite-chemise)" />
      <g className={tape ? "anim-tape" : undefined}>
        <rect x="3" y="9" width="2" height="3" className="fill-(--sprite-chemise-ombre)" />
        <rect x="11" y="9" width="2" height="3" className="fill-(--sprite-chemise-ombre)" />
      </g>
    </g>
  );
}
