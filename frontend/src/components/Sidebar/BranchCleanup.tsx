import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { PlanDeNettoyage } from "../../types/api";

/**
 * Retirer les branches que Tessera a laissées derrière lui (ticket-070).
 *
 * Chaque run crée une branche, chaque session de chat aussi, et rien ne les
 * retirait. Après une seule session d'usage réel, un projet en portait déjà
 * deux, mortes.
 *
 * **On montre avant d'agir.** Supprimer une branche est irréversible, et sur le
 * dépôt d'un client c'est le genre d'automatisme qu'on regrette : l'utilisateur
 * lit ce qui partira, et pourquoi le reste demeure, puis décide. Rien ne se
 * supprime sans un clic.
 *
 * Le composant disparaît quand il n'y a rien à dire — un encart qui annonce
 * « rien à nettoyer » est du bruit.
 */
interface BranchCleanupProps {
  projectId: string;
}

export default function BranchCleanup({ projectId }: BranchCleanupProps) {
  const [plan, setPlan] = useState<PlanDeNettoyage | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = useCallback(async () => {
    try {
      setPlan(await api.git.cleanupPlan(projectId));
    } catch {
      setPlan(null);
    }
  }, [projectId]);

  useEffect(() => {
    void charger();
  }, [charger]);

  async function supprimer() {
    if (!plan?.nettoyables.length) return;
    setEnCours(true);
    try {
      const supprimees = await api.git.cleanup(projectId, plan.nettoyables);
      setMessage(
        `${supprimees.length} branche${supprimees.length > 1 ? "s" : ""} supprimée${
          supprimees.length > 1 ? "s" : ""
        }`,
      );
      await charger();
    } catch (err: unknown) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setEnCours(false);
    }
  }

  if (!plan || (!plan.nettoyables.length && !plan.conservees.length)) return null;

  return (
    <section className="border-t border-zinc-800 px-3 py-2.5">
      <p className="mb-1.5 text-mini uppercase tracking-wider text-zinc-500">
        Branches laissées par Tessera
      </p>

      {plan.nettoyables.length > 0 && (
        <>
          <ul className="mb-2 flex flex-wrap gap-1">
            {plan.nettoyables.map((b) => (
              <li
                key={b}
                className="rounded-sm bg-zinc-800 px-1.5 py-0.5 font-mono text-micro text-zinc-300"
              >
                {b}
              </li>
            ))}
          </ul>
          <p className="mb-2 text-micro text-zinc-500">
            Elles ne contiennent rien qui ne soit déjà dans la base.
          </p>
          <button
            type="button"
            onClick={() => void supprimer()}
            disabled={enCours}
            className="rounded-sm border border-zinc-700 px-2 py-1 text-mini text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100 disabled:opacity-50"
          >
            {enCours ? "Suppression…" : `Supprimer ${plan.nettoyables.length}`}
          </button>
        </>
      )}

      {plan.conservees.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {plan.conservees.map(([branche, raison]) => (
            <li key={branche} className="text-micro text-zinc-600">
              <span className="font-mono text-zinc-500">{branche}</span> — conservée :{" "}
              {raison}
            </li>
          ))}
        </ul>
      )}

      {message && <p className="mt-2 text-micro text-green-400">{message}</p>}
    </section>
  );
}
