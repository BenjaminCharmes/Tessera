import { useState } from "react";
import { adresseDansLaSortie } from "../SupervisionView/adresse";
import { classeDeLEtat, libelleDeLEtat } from "../../design/etatDuService";
import type { UseServicesResult } from "../../hooks/useServices";
import type { ServiceActif } from "../../types/api";

/**
 * Les services du projet, là où on les lance — ticket-147.
 *
 * Le bouton vit dans l'en-tête du projet ; le retour doit donc apparaître
 * juste en dessous. La sortie existait déjà, mais dans la vue Supervision et
 * après un clic de plus : l'information était là et restait introuvable.
 *
 * Quand rien n'est déclaré, ce panneau ne disparaît pas — il dit quoi écrire.
 * Masquer la fonctionnalité répondait au symptôme sans répondre au besoin :
 * quelqu'un qui veut lancer son projet n'apprenait même pas qu'il pouvait.
 */
interface PanneauServicesProps {
  services: UseServicesResult;
  sortieDe: (projectId: string, nom: string) => string[];
  projectId: string;
  /** Pour proposer d'ouvrir `agents.json` là où il est réellement. */
  cheminDuProjet: string | null;
}

const EXEMPLE = `"services": [
  { "nom": "dev", "commande": "npm run dev" }
]`;

export default function PanneauServices({
  services,
  sortieDe,
  projectId,
  cheminDuProjet,
}: PanneauServicesProps) {
  // Un ensemble, pas un seul nom : un projet qui lance un backend **et** un
  // frontend veut voir les deux sorties en même temps. L'accordéon fermait
  // l'une en ouvrant l'autre (ticket-148).
  const [ouverts, setOuverts] = useState<ReadonlySet<string>>(new Set());

  if (!services.declare) {
    return <RienDeclare projectId={projectId} chemin={cheminDuProjet} />;
  }

  return (
    <div className="space-y-2 p-3" aria-label="Services du projet">
      {services.erreur ? (
        <p className="rounded-sm bg-red-500/15 px-2 py-1 text-mini text-red-200">
          {services.erreur}
        </p>
      ) : null}

      {services.services.map((service) => (
        <LigneDeService
          key={service.nom}
          service={service}
          lignes={lignesDe(service, sortieDe)}
          ouvert={ouverts.has(service.nom)}
          onBasculer={() =>
            setOuverts((prec) => {
              const suivant = new Set(prec);
              if (!suivant.delete(service.nom)) suivant.add(service.nom);
              return suivant;
            })
          }
        />
      ))}
    </div>
  );
}

/**
 * Ce que le service a écrit : le direct s'il est arrivé, sinon ce que le
 * backend a gardé — ticket-148.
 *
 * Le canal ne rejoue pas l'historique, et un service annonce son adresse dans
 * ses deux premières secondes. Ouvrir l'IDE ensuite affichait « n'a encore
 * rien écrit » pour un service parti depuis dix minutes.
 */
function lignesDe(
  service: ServiceActif,
  sortieDe: (projectId: string, nom: string) => string[],
): string[] {
  const direct = sortieDe(service.project_id, service.nom);
  const gardees = service.sortie ?? [];
  return direct.length >= gardees.length ? direct : gardees;
}

function LigneDeService({
  service,
  lignes,
  ouvert,
  onBasculer,
}: {
  service: ServiceActif;
  lignes: string[];
  ouvert: boolean;
  onBasculer: () => void;
}) {
  // Pas d'adresse pour un service arrêté : elle mènerait vers un serveur qui
  // n'écoute plus.
  const adresse = service.en_cours ? adresseDansLaSortie(lignes) : null;

  return (
    <div className="rounded-sm border border-zinc-800">
      <button
        type="button"
        onClick={onBasculer}
        aria-expanded={ouvert}
        className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left hover:bg-zinc-800/40"
      >
        <span className="truncate text-xs text-zinc-200">{service.nom}</span>
        <span
          className={`shrink-0 rounded-sm px-1.5 py-0.5 text-micro ${classeDeLEtat(service)}`}
        >
          {libelleDeLEtat(service)}
        </span>
      </button>

      {adresse ? (
        <a
          href={adresse}
          target="_blank"
          rel="noreferrer"
          className="block truncate px-2 pb-1.5 text-micro text-zinc-400 underline decoration-dotted hover:text-zinc-200"
        >
          {adresse}
        </a>
      ) : null}

      {ouvert ? (
        <pre
          aria-label={`Sortie de ${service.nom}`}
          className="max-h-48 overflow-auto whitespace-pre-wrap border-t border-zinc-800 bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400"
        >
          {lignes.length > 0
            ? lignes.join("\n")
            : "Ce service n'a encore rien écrit."}
        </pre>
      ) : null}
    </div>
  );
}

function RienDeclare({
  projectId,
  chemin,
}: {
  projectId: string;
  chemin: string | null;
}) {
  return (
    <div className="space-y-2 p-3" aria-label="Services du projet">
      <p className="text-xs text-zinc-400">
        « {projectId} » ne déclare aucun service. Ajoute une liste{" "}
        <code className="text-zinc-300">services</code> dans son{" "}
        <code className="text-zinc-300">agents.json</code> :
      </p>
      <pre className="overflow-x-auto rounded-sm bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400">
        {EXEMPLE}
      </pre>
      <p className="text-micro text-zinc-500">
        La commande est lancée telle quelle, sans shell : une commande par
        service, et pas de <code>&amp;&amp;</code>.
      </p>
      {chemin ? (
        <a
          href={`vscode://file/${chemin.replace(/\\/g, "/")}/agents.json`}
          className="inline-block rounded border border-zinc-700 px-2 py-1 text-mini text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
        >
          Ouvrir agents.json
        </a>
      ) : null}
    </div>
  );
}
