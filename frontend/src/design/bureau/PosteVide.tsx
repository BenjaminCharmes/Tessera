import Console from "./Console";

/**
 * Un pupitre de console sans personne, écran éteint (ticket-730) : la salle d'un
 * produit qui ne déclare aucun agent. C'est du mobilier (ADR-058) : il ne s'anime
 * pas et ne porte aucun voyant. Même grille 20 × 18 que `AgentAuPupitre`.
 */
export default function PosteVide() {
  return (
    <svg
      width="70"
      height="63"
      viewBox="0 0 20 18"
      shapeRendering="crispEdges"
      aria-hidden="true"
      data-sprite="poste-vide"
      className="overflow-visible opacity-60"
    >
      <Console allume={false} />
    </svg>
  );
}
