import type { QuotaState } from "../../types/api";

interface QuotaBadgeProps {
  quota: QuotaState | null;
}

/**
 * Consommation du quota d'abonnement (ticket-054).
 *
 * Rien n'est affiché tant que le fournisseur n'a rien remonté : un quota
 * inconnu ne doit pas se déguiser en quota confortable.
 */
export default function QuotaBadge({ quota }: QuotaBadgeProps) {
  if (!quota?.known || quota.utilization === undefined) return null;

  const percent = Math.round(quota.utilization * 100);
  const tone =
    quota.status === "rejected"
      ? "text-red-400"
      : percent >= 90
        ? "text-amber-400"
        : "text-zinc-500";

  const resets = quota.resets_at
    ? new Date(quota.resets_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <span
      className={`text-[11px] tabular-nums ${tone}`}
      title={
        quota.status === "rejected"
          ? "Quota épuisé — le fournisseur refuse les appels"
          : `Quota d'abonnement consommé${resets ? `, réinitialisé à ${resets}` : ""}`
      }
    >
      quota {percent}%{resets ? ` · ${resets}` : ""}
      {quota.run_interrupted ? " · run interrompu" : ""}
    </span>
  );
}
