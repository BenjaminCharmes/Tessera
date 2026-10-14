import { ABSENT, chiffresDuRole } from "./chiffres";
import { useChiffresAgents } from "./useChiffresAgents";

/**
 * Les chiffres d'un rôle sur 30 jours pour le projet actif (ticket-429).
 * Durée médiane et taux d'approbation manquent : aucun endpoint ne les donne.
 */
export default function ChiffresRole({
  role,
  projectId,
}: {
  role: string;
  projectId: string | null;
}) {
  const { lignes, loading, error } = useChiffresAgents(projectId);
  const chiffres = chiffresDuRole(lignes, role);
  // Pendant la lecture, « — » dirait « aucun appel » alors qu'on ne sait pas.
  const valeur = (v: string): string => (loading ? "…" : v);

  return (
    <section className="border-b border-zinc-800 px-4 py-3">
      <h3 className="mb-2 text-micro uppercase tracking-wide text-zinc-500">
        30 derniers jours
      </h3>
      {!projectId && (
        <p className="text-mini text-zinc-500">
          Ouvre un projet pour voir les chiffres de ce rôle.
        </p>
      )}
      {projectId && error && (
        <p className="text-mini text-red-400">
          Impossible de lire les chiffres : {error}
        </p>
      )}
      {projectId && !error && (
        <dl className="grid grid-cols-2 gap-3">
          <div>
            <dt className="text-micro text-zinc-500">Appels</dt>
            <dd className="text-lg font-semibold text-zinc-100">
              {valeur(chiffres.appels)}
            </dd>
          </div>
          <div>
            <dt className="text-micro text-zinc-500">Coût</dt>
            <dd className="text-lg font-semibold text-zinc-100">
              {valeur(chiffres.cout)}
            </dd>
          </div>
        </dl>
      )}
      {projectId && !error && chiffres.appels === ABSENT && !loading && (
        <p className="mt-2 text-micro text-zinc-500">
          Aucun appel de ce rôle sur la période.
        </p>
      )}
    </section>
  );
}
