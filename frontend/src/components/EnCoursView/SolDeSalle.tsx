import Agrandi from "../../design/bureau/Agrandi";
import DallePerforee from "../../design/bureau/DallePerforee";
import DallePleine from "../../design/bureau/DallePleine";

/** Assez de dalles pour la salle la plus large ; celles qui dépassent sont coupées. */
const DALLES = 60;
/** Une dalle perforée toutes les quatre, comme une allée froide. */
const PAS_PERFOREE = 4;

/**
 * Le faux plancher, posé dalle par dalle à l'échelle du mobilier — ticket-710.
 * Les dalles pleines et perforées ont la même maille : le sol ne mélange plus
 * un motif CSS à 12 px et des sprites agrandis.
 */
export default function SolDeSalle() {
  return (
    // Une demi-rangée de dalles suffit à dire « faux plancher » : la salle reste basse.
    <div data-sol="dalles" aria-hidden="true" className="flex h-8 overflow-hidden">
      <Agrandi>
        <span className="flex">
          {Array.from({ length: DALLES }, (_, i) =>
            i % PAS_PERFOREE === 1 ? <DallePerforee key={i} /> : <DallePleine key={i} />,
          )}
        </span>
      </Agrandi>
    </div>
  );
}
