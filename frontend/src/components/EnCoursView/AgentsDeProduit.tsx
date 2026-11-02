import { useEffect, useRef, useState } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import PosteVide from "../../design/bureau/PosteVide";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";
import AgentAuPupitre from "../../design/bureau/AgentAuPupitre";
import BulleDOutil from "../../design/bureau/BulleDOutil";
import { physiqueDeProduit } from "../../lib/bureau/physique";
import { prenomsDeProduit } from "../../lib/bureau/noms";
import type { AgentDeProduit } from "../../types/activiteProduit";
import AvecInfobulle from "../BureauView/AvecInfobulle";
import { formaterHeure } from "./format";
import { POSTES_VIDES, capaciteDeLaRangee, rangee } from "./rangee";

/** La largeur d'un poste à l'échelle un (le `<svg>` fait 70 px), et l'écart entre deux. */
const POSTE_PX = 74;
const ECART_PX = 24;

/** La largeur de la rangée, relue quand la fenêtre change ; `Infinity` sans `ResizeObserver`. */
function useLargeur(ref: React.RefObject<HTMLElement | null>): number {
  const [largeur, setLargeur] = useState(Infinity);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(([entree]) => {
      if (entree) setLargeur(entree.contentRect.width);
    });
    observateur.observe(el);
    return () => observateur.disconnect();
  }, [ref]);
  return largeur;
}

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
 * La rangée de postes au sol de la salle, sur une seule ligne — ticket-730. Les
 * agents qu'une app déclare dans son fichier d'activité, un par entrée —
 * tickets 673 et 710. Trop nombreux pour la largeur : le dernier poste devient un
 * badge « +N ». Sans agent, des postes vides, éteints : la salle garde sa hauteur. Comme au Bureau : un prénom, la phrase du produit dans la
 * bulle d'outil quand il travaille, une infobulle, un clic vers le journal.
 * Sans entrée, rien ne se dessine (ADR-058). Nom et libellé sont écrits par le
 * produit : ils passent par React comme du texte, jamais comme balisage.
 */
export default function AgentsDeProduit({ projectId, agents, aUnJournal, onOuvrirService }: AgentsDeProduitProps) {
  const ref = useRef<HTMLDivElement>(null);
  const echelle = useEchelleDesSprites();
  const capacite = capaciteDeLaRangee(useLargeur(ref), POSTE_PX * echelle, ECART_PX);
  const { visibles, enPlus } = rangee(agents, capacite);
  const prenoms = prenomsDeProduit(projectId, agents.map((a) => `${a.service}:${a.agent.id}`));
  return (
    <div ref={ref} data-rangee-de-postes className="flex min-w-0 flex-1 items-end justify-center">
      {agents.length === 0 ? (
        <ul aria-label="Aucun agent déclaré" data-postes-vides className="flex flex-nowrap items-end gap-x-6">
          {Array.from({ length: Math.min(POSTES_VIDES, capacite) }, (_, i) => (
            <li key={i} className="flex flex-col items-center">
              <div className="h-5" />
              <span className="p-0.5">
                <Agrandi>
                  <PosteVide />
                </Agrandi>
              </span>
            </li>
          ))}
        </ul>
      ) : (
    <ul aria-label="Agents du produit" data-agents-de-produit className="flex flex-nowrap items-end justify-center gap-x-6">
      {visibles.map(({ service, agent }) => {
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
      {enPlus > 0 && (
        <li data-agents-en-plus className="flex flex-col items-center self-center">
          <span className="rounded-sm bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300 ring-1 ring-zinc-700">
            +{enPlus} agent{enPlus > 1 ? "s" : ""}
          </span>
        </li>
      )}
    </ul>
      )}
    </div>
  );
}
