import { useTableauDuJour } from "../../hooks/useTableauDuJour";
import FenetreDeQuota from "./FenetreDeQuota";

interface TableauDuJourProps {
  /** L'horloge du Bureau : le tableau n'ouvre pas de minuteur. */
  maintenant: number;
  /** Compteur de runs clos : il change, et le tableau se relit. */
  signalRunsClos: number;
}

/**
 * Dépense du jour et quota de la session et de la semaine. Le jour est le jour
 * UTC, celui de `/usage/stats` : le dire dans le nom accessible évite de lire
 * une dépense « de la journée » qui change à une heure inattendue.
 */
export default function TableauDuJour({ maintenant, signalRunsClos }: TableauDuJourProps) {
  const { depense, session, semaine } = useTableauDuJour(maintenant, signalRunsClos);

  return (
    <aside
      aria-label="Tableau du jour, jour en UTC"
      className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2"
    >
      <p className="text-micro text-zinc-400">
        Dépense du jour{" "}
        <span className="text-sm tabular-nums text-zinc-100" data-testid="depense-du-jour">
          {depense === null ? "inconnue" : `$${depense.toFixed(2)}`}
        </span>
      </p>
      <ul className="flex flex-wrap items-center gap-x-6 gap-y-1">
        <FenetreDeQuota libelle="Session" lecture={session} maintenant={maintenant} />
        <FenetreDeQuota libelle="Semaine" lecture={semaine} maintenant={maintenant} />
      </ul>
    </aside>
  );
}
