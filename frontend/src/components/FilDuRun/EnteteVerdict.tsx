import {
  IconCheck,
  IconCross,
  IconChevronDown,
  IconChevronRight,
} from "../../design/icons";

interface EnteteVerdictProps {
  label: string;
  approved: boolean;
  verdictText: string;
  loading?: boolean;
  peutBasculer: boolean;
  ouvert: boolean;
  onToggle?: () => void;
}

/**
 * En-tête partagé par les quatre types de cartes dans le fil du run.
 *
 * Affiche : nom de l'agent | icône + verdict + chevron (si repliable)
 * ou points animés (si le traitement est en cours).
 */
export default function EnteteVerdict({
  label,
  approved,
  verdictText,
  loading = false,
  peutBasculer,
  ouvert,
  onToggle,
}: EnteteVerdictProps) {
  return (
    <button
      type="button"
      disabled={!peutBasculer}
      onClick={() => peutBasculer && onToggle?.()}
      aria-expanded={ouvert}
      className="flex w-full items-center gap-2 px-3 py-2 bg-zinc-800 text-xs font-semibold text-zinc-300 text-left disabled:cursor-default"
    >
      <span>{label}</span>

      {loading ? (
        <span className="ml-auto flex gap-0.5">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </span>
      ) : (
        <span
          className={`ml-auto flex items-center gap-1 font-normal ${
            approved ? "text-green-400" : "text-red-400"
          }`}
        >
          {approved ? <IconCheck size={12} /> : <IconCross size={12} />}
          <span>{verdictText}</span>
          {peutBasculer &&
            (ouvert ? (
              <IconChevronDown size={12} />
            ) : (
              <IconChevronRight size={12} />
            ))}
        </span>
      )}
    </button>
  );
}
