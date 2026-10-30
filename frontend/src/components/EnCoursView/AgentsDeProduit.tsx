import Agrandi from "../../design/bureau/Agrandi";
import AgentAuPupitre from "../../design/bureau/AgentAuPupitre";
import { physiqueDeProduit } from "../../lib/bureau/physique";
import type { AgentDeProduit } from "../../types/activiteProduit";

interface AgentsDeProduitProps {
  projectId: string;
  agents: readonly AgentDeProduit[];
}

/**
 * Les agents qu'une app déclare dans son fichier d'activité, un par entrée —
 * ticket-673. Sans entrée, rien ne se dessine (ADR-058). Le nom et le libellé
 * sont écrits par le produit : ils passent par React comme du texte, jamais
 * comme balisage.
 */
export default function AgentsDeProduit({ projectId, agents }: AgentsDeProduitProps) {
  if (agents.length === 0) return null;
  return (
    <ul
      aria-label="Agents du produit"
      data-agents-de-produit
      className="flex flex-wrap items-end justify-center gap-x-6 px-3 pt-2"
    >
      {agents.map((agent) => (
        <li key={agent.id} data-agent={agent.id} data-etat={agent.etat} className="flex flex-col items-center">
          <Agrandi>
            <AgentAuPupitre physique={physiqueDeProduit(projectId, agent.id)} etat={agent.etat} />
          </Agrandi>
          <span className="text-micro text-zinc-300">{agent.nom}</span>
          {agent.libelle && <span className="text-micro text-zinc-500">{agent.libelle}</span>}
          <span className="sr-only">{agent.etat === "actif" ? "au travail" : "au repos"}</span>
        </li>
      ))}
    </ul>
  );
}
