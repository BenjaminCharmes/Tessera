/**
 * Quand cet agent parle — ticket-079, ticket-094, puis refait par ticket-097.
 *
 * Il a d'abord dit « natif » / « perso », puis « requis » / « ajouté » : dans
 * les deux cas, **qui avait écrit le prompt**. Ça n'apprend rien — c'est
 * toujours un agent, et ce sera toujours le cas.
 *
 * Pire : il annonçait « requis » pour quatre prompts sur dix-sept que **rien
 * n'appelle jamais**. `testeur`, dont l'étape lance un sous-processus sans
 * agent. `architect`, que `ide-core` déclare et que personne ne charge.
 * Le badge occupait la seule place disponible avec le fait le moins utile,
 * et cachait celui-là.
 *
 * La question qu'on a devant une liste de dix-sept prompts est « lequel agit,
 * et quand ? ». C'est ce qu'il répond maintenant.
 */
export type MomentAgent = "pipeline" | "demande" | "jamais";

const LIBELLES: Record<MomentAgent, { texte: string; infobulle: string; classe: string }> = {
  pipeline: {
    texte: "pipeline",
    infobulle: "Appelé automatiquement pendant un run, sans que tu le demandes.",
    classe: "bg-zinc-700 text-zinc-200",
  },
  demande: {
    texte: "à la demande",
    infobulle: "Appelé quand tu déclenches l'action correspondante.",
    classe: "bg-blue-900 text-blue-300",
  },
  jamais: {
    texte: "jamais appelé",
    infobulle:
      "Rien ne charge ce prompt : ni le pipeline, ni une action, ni le agents.json d'un projet. Le modifier ne changera rien.",
    classe: "bg-zinc-800 text-zinc-500",
  },
};

interface AgentBadgeProps {
  moment: MomentAgent;
}

export default function AgentBadge({ moment }: AgentBadgeProps) {
  const libelle = LIBELLES[moment] ?? LIBELLES.jamais;
  return (
    <span
      title={libelle.infobulle}
      className={`shrink-0 rounded-sm px-1.5 py-0.5 text-micro font-medium ${libelle.classe}`}
    >
      {libelle.texte}
    </span>
  );
}
