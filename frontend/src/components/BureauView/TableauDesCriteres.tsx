import TableauBlanc from "../../design/bureau/TableauBlanc";
import type { StreamState } from "../../hooks/streamState";
import { useCriteresDuTicket } from "../../hooks/useCriteresDuTicket";
import {
  criteresJuges,
  libelleDuTableau,
  ligneDeLInfobulle,
  tableauDesCriteres,
  ticketDuRun,
} from "../../lib/bureau/criteres";
import AvecInfobulle from "./AvecInfobulle";

interface TableauDesCriteresProps {
  projet: string;
  etat: StreamState;
}

/**
 * Le tableau blanc d'une pièce : les critères du validateur une fois son verdict
 * rendu, sinon ceux du fichier du ticket, tous gris. Vierge quand on ne sait rien.
 * Le fichier n'est lu que tant que rien n'est jugé.
 */
export default function TableauDesCriteres({ projet, etat }: TableauDesCriteresProps) {
  const juges = criteresJuges(etat);
  const attendus = useCriteresDuTicket(juges === null ? projet : null, ticketDuRun(etat));
  const tableau = tableauDesCriteres(juges, attendus);
  const label = libelleDuTableau(tableau);
  const sprite = <TableauBlanc cases={tableau.lignes.map((l) => l.etat)} />;

  // Sans critère, l'infobulle n'aurait rien à lister : le tableau n'est qu'une image.
  if (tableau.lignes.length === 0) {
    return (
      <span role="img" aria-label={label} className="block">
        {sprite}
      </span>
    );
  }
  return (
    <AvecInfobulle
      label={label}
      className="block"
      infobulle={
        <ul>
          {tableau.lignes.map((ligne, i) => (
            <li key={i}>{ligneDeLInfobulle(ligne, i)}</li>
          ))}
        </ul>
      }
    >
      {sprite}
    </AvecInfobulle>
  );
}
