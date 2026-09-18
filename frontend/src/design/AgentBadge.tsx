/**
 * Ce que le badge dit d'un agent — ticket-079, reformulé par ticket-094.
 *
 * Il disait « natif » / « perso », c'est-à-dire **qui a écrit le prompt**. Ça
 * n'apprend rien : l'agent qui écrit un prompt depuis l'IDE est le même que
 * celui qui en livre un avec le dépôt, et ce sera toujours le cas.
 *
 * Ce qui compte est la conséquence : **qu'est-ce qui casse s'il disparaît ?**
 * Le produit charge `codeur.md` par son nom, et un projet du dépôt déclare
 * `analyste-carriere.md` dans son `agents.json` — les deux manquent à
 * quelqu'un. Un `expert-sql.md` que rien ne nomme peut disparaître sans rien
 * casser. Le badge dit ça, et c'est aussi ce que la suppression refuse.
 */
interface AgentBadgeProps {
  /** Quelque chose dépend de ce prompt par son nom : il ne peut pas disparaître. */
  natif: boolean;
}

export default function AgentBadge({ natif }: AgentBadgeProps) {
  return (
    <span
      title={
        natif
          ? "Le produit ou un projet déclare ce prompt par son nom. Tu peux le modifier — le supprimer casserait leurs runs."
          : "Rien ne le déclare par son nom. Tu peux le modifier et le supprimer."
      }
      className={`shrink-0 rounded px-1.5 py-0.5 text-micro font-medium ${
        natif ? "bg-blue-900 text-blue-300" : "bg-violet-500/20 text-violet-200"
      }`}
    >
      {natif ? "requis" : "ajouté"}
    </span>
  );
}
