import { useState } from "react";
import type { StreamState } from "../../hooks/streamState";
import { useAlerteSonore } from "../../hooks/useAlerteSonore";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { useWeekEmployee } from "../../hooks/useWeekEmployee";
import { contenuAToi } from "../../lib/bureau/aToi";
import type { RunActif } from "../../types/api";
import ColonneAToi from "./ColonneAToi";
import type { ReglageSon } from "./ColonneAToi";
import PanneauAgentChoisi from "./PanneauAgentChoisi";
import type { AgentChoisi } from "./PanneauAgentChoisi";
import Piece from "./Piece";
import SallesCommunes from "./SallesCommunes";

export interface ProjetDuBureau {
  nom: string;
  etat: StreamState;
  /** Le run vivant du projet, quand on le connaît. */
  runId?: string | null;
  /** Le run lui-même, pour le chrono, le fil et le rangement. */
  run?: RunActif;
}

interface BureauViewProps {
  projets: readonly ProjetDuBureau[];
  /** Compteur d'événements de service de la supervision (`signalServices`). */
  signalServices?: number;
  /** Le canal de la supervision : la réponse d'une question passe par `{ type: "answer" }`. */
  envoyer: (runId: string, payload: Record<string, string>) => void;
  /** Le réglage « Son » de la question (ticket-554), tenu par la cloche : le Bureau n'en a pas un à lui. */
  son: ReglageSon;
  /** Les projets sans run : pas de pièce, mais l'employé de la semaine peut en venir. */
  auRepos?: readonly string[];
  /** Ouvre le fil d'un run (ticket-567). */
  onOuvrir?: (runId: string) => void;
  /** Range un run clos (ticket-567). */
  onRanger?: (runId: string) => void;
  /** Choisit un projet et ouvre son onglet Tickets : la porte de sa pièce (ticket-602). */
  onOpenProject?: (projet: string) => void;
}

/**
 * Les pièces des projets qui ont un run, une par ligne, quel que soit leur nombre.
 * L'horloge se monte ici, une seule fois pour toute la vue.
 */
export default function BureauView({
  projets,
  signalServices = 0,
  envoyer,
  son,
  auRepos = [],
  onOuvrir,
  onRanger,
  onOpenProject,
}: BureauViewProps) {
  const maintenant = useSanteDuBureau();
  // L'agent choisi : seul le couple est retenu, ses lignes se relisent à chaque rendu.
  const [choix, setChoix] = useState<AgentChoisi | null>(null);
  const projetChoisi = projets.find((p) => p.nom === choix?.projet);

  // Un run qui se clôt fait relire l'employé de la semaine. Un compte et non un événement :
  // la vue ne reçoit que des états, et `runClosed` y est posé par `run_closed`.
  const runsClos = projets.filter((p) => p.etat.runClosed).length;
  const employe = useWeekEmployee([...projets.map((p) => p.nom), ...auRepos], maintenant, runsClos);

  const aToi = contenuAToi(projets, maintenant);
  useAlerteSonore(
    aToi.questions.map((q) => q.projet),
    son.actif,
  );

  return (
    <div className="flex items-start gap-3.5">
      <div className="flex min-w-0 flex-1 flex-col gap-3.5">
        <SallesCommunes projets={projets} maintenant={maintenant} employe={employe} />
        {/* Une pièce par projet, empilées sur toute la largeur : la vue défile en hauteur. */}
        <div className="flex flex-col gap-3.5" data-mode="pieces">
          {projets.map(({ nom, etat, runId = null, run }) => (
            <Piece
              key={nom}
              projet={nom}
              etat={etat}
              maintenant={maintenant}
              runId={runId}
              signalServices={signalServices}
              run={run}
              onOuvrir={onOuvrir}
              onRanger={onRanger}
              onChoisir={(projet, poste) => setChoix({ projet, poste })}
              onOpenProject={onOpenProject}
              sonActif={son.actif}
            />
          ))}
        </div>
      </div>
      <div className="flex w-72 shrink-0 flex-col gap-3.5">
        <ColonneAToi
          contenu={aToi}
          maintenant={maintenant}
          onAnswer={(runId, text) => envoyer(runId, { type: "answer", text })}
          son={son}
        />
        <PanneauAgentChoisi
          choix={choix}
          etat={projetChoisi?.etat}
          run={projetChoisi?.run}
          maintenant={maintenant}
          onOuvrir={onOuvrir}
        />
      </div>
    </div>
  );
}
