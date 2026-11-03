import Agrandi from "../../design/bureau/Agrandi";
import Tuile from "../../design/bureau/Tuile";

/** Assez de faux plancher pour la salle la plus large ; ce qui dépasse est coupé. */
const LARGEUR = 2160;

/**
 * Le faux plancher, à l'échelle du mobilier (ticket-710, ticket-727) : une tuile de
 * quatre dalles, la deuxième perforée comme une allée froide, répétée sur toute la
 * largeur. Une seule surface au lieu d'un sprite par dalle.
 */
export default function SolDeSalle() {
  return (
    // Une demi-rangée de dalles suffit à dire « faux plancher » : la salle reste basse.
    <div data-sol="dalles" aria-hidden="true" className="flex h-8 overflow-hidden">
      <Agrandi>
        <span className="relative block h-9" style={{ width: LARGEUR }}>
          <Tuile motif="dalles" moment="jour" />
        </span>
      </Agrandi>
    </div>
  );
}
