import Agrandi from "../../design/bureau/Agrandi";
import AgentAuPupitre from "../../design/bureau/AgentAuPupitre";
import BulleDOutil from "../../design/bureau/BulleDOutil";
import { physiqueDeProduit } from "../../lib/bureau/physique";
import { prenomsDeProduit } from "../../lib/bureau/noms";
import type { AgentDeProduit } from "../../types/activiteProduit";
import AvecInfobulle from "../BureauView/AvecInfobulle";
import { formaterHeure } from "./format";

/** Un agent et le service du produit qui le déclare. */
export interface AgentDuService {
  service: string;
  agent: AgentDeProduit;
}

interface AgentsDeProduitProps {
  projectId: string;
  agents: readonly AgentDuService[];
  /** Le service a un journal à ouvrir (lancé par l'IDE) ; sinon l'agent n'est pas cliquable. */
  aUnJournal: (service: string) => boolean;
  /** Un clic sur un agent ouvre le journal de son service. */
  onOuvrirService: (service: string) => void;
}

/**
 * Les agents qu'une app déclare dans son fichier d'activité, un par entrée —
 * tickets 673 et 710. Comme au Bureau : un prénom, la phrase du produit dans la
 * bulle d'outil quand il travaille, une infobulle, un clic vers le journal.
 * Sans entrée, rien ne se dessine (ADR-058). Nom et libellé sont écrits par le
 * produit : ils passent par React comme du texte, jamais comme balisage.
 */
export default function AgentsDeProduit({ projectId, agents, aUnJournal, onOuvrirService }: AgentsDeProduitProps) {
  if (agents.length === 0) return null;
  const prenoms = prenomsDeProduit(projectId, agents.map((a) => `${a.service}:${a.agent.id}`));
  return (
    <ul aria-label="Agents du produit" data-agents-de-produit className="flex flex-wrap items-end justify-center gap-x-6">
      {agents.map(({ service, agent }) => {
        const cle = `${service}:${agent.id}`;
        const prenom = prenoms.get(cle) ?? agent.nom;
        const journal = aUnJournal(service);
        const actif = agent.etat === "actif";
        return (
          <li key={`${service}:${agent.id}`} data-agent={agent.id} data-etat={agent.etat} className="flex flex-col items-center">
            <div className="flex h-5 max-w-full items-end">
              {actif && agent.libelle && <BulleDOutil phrase={agent.libelle} />}
            </div>
            <AvecInfobulle
              label={`${prenom}, ${agent.nom}, ${actif ? "au travail" : "au repos"}`}
              className="rounded-md p-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
              onActiver={journal ? () => onOuvrirService(service) : undefined}
              infobulle={
                <>
                  <p className="font-semibold text-zinc-100">
                    {prenom} · {agent.nom}
                  </p>
                  <p>
                    {actif ? "Au travail" : "Au repos"}
                    {agent.depuis ? ` depuis ${formaterHeure(agent.depuis)}` : ""}
                  </p>
                  {agent.libelle && <p className="text-zinc-400">{agent.libelle}</p>}
                  <p className="text-zinc-500">Service {service}{journal ? " — clic : son journal" : ""}</p>
                </>
              }
            >
              <Agrandi>
                <AgentAuPupitre physique={physiqueDeProduit(projectId, cle)} etat={agent.etat} />
              </Agrandi>
            </AvecInfobulle>
          </li>
        );
      })}
    </ul>
  );
}
