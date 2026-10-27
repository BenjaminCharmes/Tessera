interface PersonnageProps {
  /** Les mains tapent : vrai quand l'agent travaille. */
  tape?: boolean;
  /** Assis au poste (défaut), ou debout à côté, tasse à la main : l'agent a fini. */
  pose?: "assis" | "debout";
}

/** Le personnage debout à gauche du bureau, tasse à la main, dans la grille 16 × 18 du poste. */
function PersonnageDebout() {
  return (
    <g data-sprite="personnage" data-pose="debout">
      <rect x="1" y="3" width="3" height="1" className="fill-(--sprite-cheveux)" />
      <rect x="1" y="4" width="3" height="3" className="fill-(--sprite-peau)" />
      <rect x="1" y="5" width="1" height="1" className="fill-zinc-900" />
      <rect x="3" y="5" width="1" height="1" className="fill-zinc-900" />
      <rect x="1" y="7" width="3" height="6" className="fill-(--sprite-chemise)" />
      <rect x="1" y="13" width="1" height="5" className="fill-zinc-800" />
      <rect x="3" y="13" width="1" height="5" className="fill-zinc-800" />
      <rect x="4" y="9" width="1" height="2" className="fill-(--sprite-chemise-ombre)" />
      <rect x="4" y="7" width="2" height="2" className="fill-zinc-200" />
    </g>
  );
}

/** Le personnage d'un poste : assis (immobile ou à taper), ou debout une fois fini. */
export default function Personnage({ tape = false, pose = "assis" }: PersonnageProps) {
  if (pose === "debout") return <PersonnageDebout />;
  return (
    <g data-sprite="personnage" data-pose="assis">
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
