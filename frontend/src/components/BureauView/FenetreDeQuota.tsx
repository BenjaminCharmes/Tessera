import { heureDeReprise } from "../../lib/bureau/heureDeReprise";
import type { QuotaWindowReading } from "../../lib/quota";

interface FenetreDeQuotaProps {
  libelle: string;
  /** `null` : la fenêtre n'a jamais été relevée. */
  lecture: QuotaWindowReading | null;
  maintenant: number;
}

function teinte(pourcent: number, refuse: boolean): string {
  if (refuse || pourcent >= 95) return "bg-red-500";
  return pourcent >= 80 ? "bg-amber-500" : "bg-green-500";
}

/**
 * Une fenêtre de quota : barre, pourcentage et heure de reprise. Sans relevé,
 * « inconnu » et aucune barre : une barre à 0 % dirait qu'il reste tout.
 */
export default function FenetreDeQuota({ libelle, lecture, maintenant }: FenetreDeQuotaProps) {
  if (lecture === null) {
    return (
      <li className="flex items-center gap-2 text-micro text-zinc-400">
        <span className="w-14">{libelle}</span>
        <span>inconnu</span>
      </li>
    );
  }

  const pourcent = Math.round(lecture.utilization * 100);
  const reprise = lecture.resets_at ? heureDeReprise(lecture.resets_at, maintenant) : null;

  return (
    <li className="flex items-center gap-2 text-micro text-zinc-300">
      <span className="w-14">{libelle}</span>
      <div
        role="progressbar"
        aria-label={`${libelle}, ${pourcent} %`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pourcent}
        className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800"
      >
        <div
          className={`h-full ${teinte(pourcent, lecture.status === "rejected")}`}
          style={{ width: `${Math.min(Math.max(pourcent, 0), 100)}%` }}
        />
      </div>
      <span className="tabular-nums">{pourcent} %</span>
      {reprise !== null && lecture.resets_at && (
        <span className="text-zinc-400">
          reprise <time dateTime={lecture.resets_at}>{reprise}</time>
        </span>
      )}
    </li>
  );
}
