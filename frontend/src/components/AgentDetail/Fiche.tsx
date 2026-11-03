import ChiffresRole from "./ChiffresRole";
import Definition from "./Definition";
import ModelPicker from "./ModelPicker";
import Verdicts from "./Verdicts";
import { ROLES_A_VERDICT } from "./chiffres";

/**
 * La fiche d'un rôle (ticket-429) : à gauche ce qu'il dit — prompt et derniers
 * verdicts —, à droite ce qu'il est sur ce projet — configuration et chiffres.
 */
export default function Fiche({
  role,
  projectId,
}: {
  role: string | null;
  projectId: string | null;
}) {
  if (!role) {
    return (
      <p className="px-4 py-3 text-xs text-zinc-500">
        Sélectionne un agent dans la liste pour lire sa définition.
      </p>
    );
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* `key` : la vue, le brouillon et le message repartent de zéro avec
            l'agent sans qu'un effet ait à les remettre à zéro (ticket-123). */}
        <Definition key={role} role={role} />
        {projectId && ROLES_A_VERDICT.includes(role) && (
          <Verdicts projectId={projectId} />
        )}
      </div>
      <aside
        aria-label="Configuration et chiffres"
        className="w-80 shrink-0 overflow-auto border-l border-zinc-800"
      >
        {projectId && <ModelPicker projectId={projectId} role={role} />}
        <ChiffresRole role={role} projectId={projectId} />
      </aside>
    </div>
  );
}
