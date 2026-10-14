import { useState } from "react";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import Comparer from "./Comparer";
import Fiche from "./Fiche";

/**
 * L'onglet Agents au centre : la fiche d'un rôle, ou tous les rôles comparés
 * (ticket-429). La fiche reprend la définition d'un agent de ticket-076 — son
 * prompt système, première chose à lire quand il se comporte mal.
 *
 * Le rail dit *quel* agent, le centre montre *ce qu'il est*.
 */
interface AgentDetailProps {
  role: string | null;
  /** Le projet actif : le modèle se règle projet par projet (ticket-080). */
  projectId?: string | null;
  /** Choisit un rôle, comme le rail : le tableau « Comparer » l'utilise. */
  onSelectRole?: (role: string) => void;
}

type Vue = "fiche" | "comparer";

const VUES: { cle: Vue; libelle: string }[] = [
  { cle: "fiche", libelle: "Fiche" },
  { cle: "comparer", libelle: "Comparer" },
];

export default function AgentDetail({
  role,
  projectId = null,
  onSelectRole,
}: AgentDetailProps) {
  const [vue, setVue] = useState<Vue>("fiche");

  function ouvrirLaFiche(cible: string) {
    onSelectRole?.(cible);
    setVue("fiche");
  }

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Agents</RegionTitle>
        <div
          role="group"
          aria-label="Vue"
          className="flex items-center gap-0.5 rounded-sm border border-zinc-700 p-0.5"
        >
          {VUES.map((v) => (
            <button
              key={v.cle}
              type="button"
              aria-pressed={vue === v.cle}
              onClick={() => setVue(v.cle)}
              className={`rounded-sm px-2 py-0.5 text-mini transition-colors ${
                vue === v.cle
                  ? "bg-violet-500/15 text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {v.libelle}
            </button>
          ))}
        </div>
      </div>
      {vue === "fiche" ? (
        <Fiche role={role} projectId={projectId} />
      ) : (
        <Comparer projectId={projectId} onOpen={ouvrirLaFiche} />
      )}
    </div>
  );
}
