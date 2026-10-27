import TableauBlanc from "../../design/bureau/TableauBlanc";
import type { StreamState } from "../../hooks/streamState";
import { useCriteresDuTicket } from "../../hooks/useCriteresDuTicket";
import {
  criteresJuges,
  etatDit,
  libelleDuTableau,
  tableauDesCriteres,
  ticketDuRun,
} from "../../lib/bureau/criteres";
import type { EtatCase, LigneDuTableau } from "../../lib/bureau/criteres";
import AvecInfobulle from "./AvecInfobulle";

const PUCES: Record<EtatCase, string> = {
  attente: "bg-zinc-600",
  passe: "bg-green-500",
  echoue: "bg-red-500",
};

/** Le texte d'un critère, ses `identifiants` en police fixe plutôt qu'entre accents graves. */
function TexteDuCritere({ texte }: { texte: string }) {
  return (
    <>
      {texte.split("`").map((morceau, i) =>
        i % 2 === 1 ? (
          <code key={i} className="rounded-sm bg-zinc-800 px-0.5 font-mono text-micro text-zinc-100">
            {morceau}
          </code>
        ) : (
          morceau
        ),
      )}
    </>
  );
}

/** Une ligne de l'infobulle : une puce de couleur, le critère, puis son état en toutes lettres. */
function LigneDuCritere({ ligne, rang }: { ligne: LigneDuTableau; rang: number }) {
  return (
    <li className="flex gap-2 leading-snug">
      <span aria-hidden="true" className={`mt-1.5 size-1.5 shrink-0 rounded-full ${PUCES[ligne.etat]}`} />
      <span>
        <TexteDuCritere texte={ligne.texte || `Critère ${rang + 1}`} />
        <span className="text-zinc-500"> — {etatDit(ligne.etat)}</span>
      </span>
    </li>
  );
}

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
      large
      infobulle={
        <ul className="flex flex-col gap-1.5 py-0.5">
          {tableau.lignes.map((ligne, i) => (
            <LigneDuCritere key={i} ligne={ligne} rang={i} />
          ))}
        </ul>
      }
    >
      {sprite}
    </AvecInfobulle>
  );
}
