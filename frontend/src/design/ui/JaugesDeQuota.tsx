import type { QuotaWindowReading } from "../../lib/quota";

/** Les fenêtres affichées, dans l'ordre : la session puis la semaine. Une autre fenêtre ne s'invente pas. */
const FENETRES: readonly { cle: string; libelle: string }[] = [
  { cle: "five_hour", libelle: "Session (5 h)" },
  { cle: "seven_day", libelle: "Semaine" },
];

/** Au-delà, la jauge passe à l'ambre : il reste peu avant la limite (ADR-026). */
const SEUIL_AMBRE = 0.85;

function remiseAZero(iso: string | null): string {
  const t = iso === null ? Number.NaN : Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  return new Date(t).toLocaleString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

interface JaugesDeQuotaProps {
  fenetres: Record<string, QuotaWindowReading | undefined> | undefined;
  /** `affiche` : sur le mur d'une salle, en police mono ; `carte` : dans Statistiques. */
  variante?: "affiche" | "carte";
}

/**
 * Le quota réel de l'abonnement, par fenêtre — ticket-726. Lu par `GET /usage/quota`
 * (ticket-558) : le SDK ne rend un relevé que lorsque l'état change, et rien n'est
 * gardé d'un redémarrage à l'autre. Une fenêtre sans relevé le dit, plutôt que
 * d'afficher un 0 % qui voudrait dire « tout reste ».
 */
export default function JaugesDeQuota({ fenetres, variante = "carte" }: JaugesDeQuotaProps) {
  const police = variante === "affiche" ? "font-mono text-micro" : "text-xs";
  return (
    <ul className={`flex flex-col gap-2 ${police} text-zinc-200`} aria-label="Quota de l'abonnement">
      {FENETRES.map(({ cle, libelle }) => {
        const releve = fenetres?.[cle];
        const part = releve ? Math.round(releve.utilization * 100) : null;
        return (
          <li key={cle} data-fenetre={cle}>
            <div className="flex justify-between gap-3 text-zinc-400">
              <span>{libelle}</span>
              <span>{part === null ? "pas de relevé" : `${part} %`}</span>
            </div>
            <div className="my-1 h-2 bg-zinc-900">
              {releve && (
                <div
                  className={`h-2 ${releve.utilization >= SEUIL_AMBRE ? "bg-amber-400" : "bg-blue-400"}`}
                  style={{ width: `${Math.min(100, part ?? 0)}%` }}
                />
              )}
            </div>
            {releve && <div className="text-zinc-400">remis à zéro {remiseAZero(releve.resets_at)}</div>}
          </li>
        );
      })}
    </ul>
  );
}
