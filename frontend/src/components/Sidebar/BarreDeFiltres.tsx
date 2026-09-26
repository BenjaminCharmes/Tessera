import {
  FILTRES_VIDES,
  TRIS,
  filtresActifs,
  type FiltresTickets,
  type TriDesTickets,
} from "../../lib/filtresTickets";
import type { TicketPriority, TicketType } from "../../types/api";

/**
 * Chercher, filtrer et trier les tickets — ticket-195.
 *
 * Le compteur « n sur N » dit ce que les filtres cachent : une liste vide
 * sans explication se lit comme un projet sans tickets.
 */
const TYPES: TicketType[] = ["feat", "fix", "chore", "docs", "refactor", "test", "design"];
const PRIORITES: TicketPriority[] = ["critical", "high", "medium", "low"];

const CHAMP =
  "rounded-sm border border-zinc-700 bg-zinc-950 px-1.5 py-0.5 text-micro text-zinc-300 outline-hidden focus:border-zinc-500";

interface BarreDeFiltresProps {
  filtres: FiltresTickets;
  onChange: (f: FiltresTickets) => void;
  retenus: number;
  total: number;
  agents: string[];
}

export default function BarreDeFiltres({
  filtres,
  onChange,
  retenus,
  total,
  agents,
}: BarreDeFiltresProps) {
  const actifs = filtresActifs(filtres);
  return (
    <div className="flex flex-col gap-1 border-b border-zinc-800 px-3 py-1.5">
      <input
        type="search"
        aria-label="Chercher un ticket"
        placeholder="Chercher (id, titre, corps)"
        value={filtres.texte}
        onChange={(e) => onChange({ ...filtres, texte: e.target.value })}
        className={`${CHAMP} w-full`}
      />
      <div className="flex flex-wrap items-center gap-1">
        <select
          aria-label="Type"
          value={filtres.type}
          onChange={(e) => onChange({ ...filtres, type: e.target.value as TicketType | "" })}
          className={CHAMP}
        >
          <option value="">type</option>
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          aria-label="Priorité"
          value={filtres.priorite}
          onChange={(e) =>
            onChange({ ...filtres, priorite: e.target.value as TicketPriority | "" })
          }
          className={CHAMP}
        >
          <option value="">priorité</option>
          {PRIORITES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        {agents.length > 1 && (
          <select
            aria-label="Agent"
            value={filtres.agent}
            onChange={(e) => onChange({ ...filtres, agent: e.target.value })}
            className={CHAMP}
          >
            <option value="">agent</option>
            {agents.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        )}
        <select
          aria-label="Tri"
          value={filtres.tri}
          onChange={(e) => onChange({ ...filtres, tri: e.target.value as TriDesTickets })}
          className={CHAMP}
        >
          {TRIS.map((t) => (
            <option key={t.valeur} value={t.valeur}>
              tri : {t.label.toLowerCase()}
            </option>
          ))}
        </select>
        <span className="ml-auto text-micro text-zinc-500" aria-live="polite">
          {actifs ? `${retenus} sur ${total}` : `${total}`}
        </span>
        {actifs && (
          <button
            type="button"
            onClick={() => onChange({ ...FILTRES_VIDES, tri: filtres.tri })}
            className="text-micro text-zinc-500 hover:text-zinc-300"
          >
            effacer
          </button>
        )}
      </div>
    </div>
  );
}
