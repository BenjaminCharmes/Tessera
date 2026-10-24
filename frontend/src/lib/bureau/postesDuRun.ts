import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";

/** Les cinq postes de la pièce, dans l'ordre du pipeline. */
export type PosteId = "codeur" | "testeur" | "securite" | "reviewer" | "validateur";

/** `occupe` : l'étape tourne ; `fait` : elle a rendu au moins un résultat ; `libre` : rien à dire. */
export type EtatPoste = "occupe" | "fait" | "libre";

export interface PosteDuRun {
  poste: PosteId;
  etat: EtatPoste;
}

export const POSTES: readonly PosteId[] = [
  "codeur",
  "testeur",
  "securite",
  "reviewer",
  "validateur",
];

type Transition = "debut" | "fin";

interface Releve {
  occupe: boolean;
  fait: boolean;
}

/**
 * Le poste et la transition qu'un événement annonce, ou null s'il n'en annonce aucun.
 *
 * L'architecte produit à la place du codeur sur un ticket `design` : même poste.
 * Le testeur n'a pas d'événement de départ (`test_result` seul, à la fin), donc
 * il n'est jamais `occupe` : le dire sans donnée serait décoratif.
 */
function transitionDe(ev: OrchestratorEvent): { poste: PosteId; transition: Transition } | null {
  switch (ev.type) {
    case "agent_started":
    case "agent_done": {
      const transition = ev.type === "agent_started" ? "debut" : "fin";
      if (ev.agent === "codeur" || ev.agent === "architect") return { poste: "codeur", transition };
      if (ev.agent === "reviewer") return { poste: "reviewer", transition };
      return null;
    }
    case "test_result":
      return { poste: "testeur", transition: "fin" };
    case "security_audit_started":
      return { poste: "securite", transition: "debut" };
    case "security_audit_done":
      return { poste: "securite", transition: "fin" };
    case "validation_started":
      return { poste: "validateur", transition: "debut" };
    case "validation_done":
      return { poste: "validateur", transition: "fin" };
    default:
      return null;
  }
}

function releveVierge(): Map<PosteId, Releve> {
  return new Map(POSTES.map((poste) => [poste, { occupe: false, fait: false }]));
}

function rejouer(evenements: readonly OrchestratorEvent[]): Map<PosteId, Releve> {
  const releves = releveVierge();
  for (const ev of evenements) {
    if (ev.type === "pipeline_done") {
      // Plus aucun agent ne tourne une fois le verdict rendu.
      for (const r of releves.values()) r.occupe = false;
      continue;
    }
    const t = transitionDe(ev);
    const releve = t ? releves.get(t.poste) : undefined;
    if (!t || !releve) continue;
    if (t.transition === "debut") releve.occupe = true;
    else Object.assign(releve, { occupe: false, fait: true });
  }
  return releves;
}

function etatDuReleve(releve: Releve, runClos: boolean): EtatPoste {
  if (releve.occupe && !runClos) return "occupe";
  return releve.fait ? "fait" : "libre";
}

/**
 * L'état des cinq postes, lu dans `ticketEvents`.
 *
 * `run_closed` remet `etape` et `etapesEnCours` à vide : les étapes d'un run
 * clos ne se lisent que dans les événements. Un agent démarré mais jamais
 * terminé dans un run clos (arrêt) n'est plus `occupe` : il reprend l'état qu'il
 * avait avant de démarrer.
 */
export function postesDuRun(etat: StreamState): PosteDuRun[] {
  const releves = rejouer(etat.ticketEvents);
  return POSTES.map((poste) => ({
    poste,
    etat: etatDuReleve(releves.get(poste) ?? { occupe: false, fait: false }, etat.runClosed),
  }));
}
