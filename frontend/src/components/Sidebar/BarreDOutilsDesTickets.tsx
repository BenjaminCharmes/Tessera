import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconBoard, IconBolt, IconPlay, IconPlus } from "../../design/icons";

interface BarreDOutilsDesTicketsProps {
  showKanban: boolean;
  /** Un run tourne, mais le centre montre autre chose (ticket-178). */
  runCache?: boolean;
  onVoirLeRun?: () => void;
  onPlanifier: () => void;
  onCreer: () => void;
  onToggleKanban: () => void;
}

/** Title band of the ticket column: plan, create, back to the run, kanban toggle. */
export default function BarreDOutilsDesTickets({
  showKanban,
  runCache,
  onVoirLeRun,
  onPlanifier,
  onCreer,
  onToggleKanban,
}: BarreDOutilsDesTicketsProps) {
  return (
    <div className={`${BAND} justify-between border-b border-zinc-700 px-3`}>
      {/* Pas le nom du projet : `ProjectHeader` le porte juste au-dessus,
          et il apparaissait deux fois à quarante pixels d'intervalle. */}
      <RegionTitle>Tickets</RegionTitle>
      <div className="flex items-center gap-1 shrink-0 ml-2">
        <button
          onClick={onPlanifier}
          title="Planifier une évolution"
          aria-label="Planifier une évolution"
          className="w-6 h-6 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-sm leading-none"
        >
          <IconBolt size={14} />
        </button>
        <button
          onClick={onCreer}
          title="Nouveau ticket"
          aria-label="Créer un ticket"
          className="w-6 h-6 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-base leading-none"
        >
          <IconPlus size={14} />
        </button>
        {/* Sans ce retour, quitter la vue du run la rendait injoignable
            depuis cet onglet jusqu'à la fin du run (ticket-178). */}
        {runCache && onVoirLeRun ? (
          <button
            onClick={onVoirLeRun}
            title="Revenir au run en cours"
            aria-label="Revenir au run en cours"
            className="flex h-6 w-6 items-center justify-center rounded-sm text-blue-300 transition-colors hover:bg-zinc-700"
          >
            <IconPlay size={14} />
          </button>
        ) : null}
        <button
          onClick={onToggleKanban}
          title={showKanban ? "Éditeur" : "Vue tableau"}
          aria-label={showKanban ? "Éditeur" : "Vue tableau"}
          className={`w-6 h-6 flex items-center justify-center rounded text-sm transition-colors ${
            showKanban
              ? "bg-zinc-600 text-white"
              : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700"
          }`}
        >
          <IconBoard size={14} />
        </button>
      </div>
    </div>
  );
}
