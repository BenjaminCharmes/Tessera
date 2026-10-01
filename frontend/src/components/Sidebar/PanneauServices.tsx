import { useState } from "react";
import InfoTip from "../../design/InfoTip";
import { adressesDansLaSortie } from "../SupervisionView/adresse";
import AdresseDuService from "../SupervisionView/AdresseDuService";
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
 * `RienDeclare` est atteignable depuis ticket-156 : `PanneauxDuProjet` ouvre
 * ce panneau d'office quand rien n'est déclaré, comme il le fait déjà pour le
 * projet qui fait tourner l'IDE. Une absence de bouton s'explique là où le
 * bouton manquerait, pas ailleurs.
 *
 * Replié par défaut, et sans le moindre geste de lancement : ADR-042 pose que
 * ne rien déclarer **est** la réponse « ce projet ne se lance pas depuis
 * l'IDE ». Beaucoup de projets sont dans ce cas pour de bon — des scripts — et
 * ce qu'on leur montre par défaut se paie sur chacun d'eux. D'où une ligne,
 * et le détail seulement si on le demande.
 */
interface PanneauServicesProps {
  services: UseServicesResult;
  sortieDe: (projectId: string, nom: string) => string[];
  projectId: string;
  /** Pour proposer d'ouvrir `agents.json` là où il est réellement. */
  cheminDuProjet: string | null;
  /** Ce projet exécute l'IDE : il n'y a rien à lancer (ticket-152). */
  faitTournerLIde?: boolean;
}

const EXEMPLE = `"services": [
  { "nom": "dev", "commande": "npm run dev" }
]`;

export default function PanneauServices({
  services,
  sortieDe,
  projectId,
  cheminDuProjet,
  faitTournerLIde = false,
}: PanneauServicesProps) {
  // Un ensemble, pas un seul nom : un projet qui lance un backend **et** un
  // frontend veut voir les deux sorties en même temps. L'accordéon fermait
  // l'une en ouvrant l'autre (ticket-148).
  const [ouverts, setOuverts] = useState<ReadonlySet<string>>(new Set());

  if (faitTournerLIde) {
    return <CestLIde projectId={projectId} />;
  }

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
  const adresses = service.en_cours
    ? adressesDansLaSortie(lignes, window.location.origin)
    : [];

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

      {adresses.length > 0 ? (
        <span className="flex flex-wrap gap-1 px-2 pb-1.5">
          {adresses.map((adresse) => (
            <AdresseDuService key={adresse.url} {...adresse} />
          ))}
        </span>
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

/**
 * Le projet bootstrap, qui exécute l'IDE — ticket-152.
 *
 * Lui proposer « Lancer » démarrerait un second backend sur un port déjà
 * pris, et le cas utile n'existe pas : il faut que l'IDE tourne pour qu'on
 * voie cet écran. Il vaut mieux dire ce qu'il est.
 */
function CestLIde({ projectId }: { projectId: string }) {
  // Une ligne, pas quatre : dire qu'il n'y a rien à faire ne mérite pas le
  // quart du panneau. Le détail reste au survol (ticket-154).
  return (
    <p
      className="p-3 text-micro text-zinc-500"
      aria-label="Services du projet"
      title={`« ${projectId} » fait tourner l'IDE que tu utilises en ce moment. Il n'y a rien à lancer : ses serveurs sont déjà là, démarrés hors de l'IDE. Pour les arrêter ou lire leurs journaux, passe par le terminal qui les a lancés.`}
    >
      {`« ${projectId} » fait tourner l'IDE.`}
    </p>
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
    <div className="p-3" aria-label="Services du projet">
      <details className="group">
        <summary className="cursor-pointer list-none text-micro text-zinc-500 transition-colors hover:text-zinc-300">
          « {projectId} » ne déclare aucun service.{" "}
          <span className="text-zinc-600 group-open:hidden">
            Comment en déclarer un ?
          </span>
        </summary>
        <div className="space-y-2 pt-2">
          <p className="text-xs text-zinc-400">
            Ajoute une liste <code className="text-zinc-300">services</code>{" "}
            dans son <code className="text-zinc-300">agents.json</code> :
          </p>
          <pre className="overflow-x-auto rounded-sm bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400">
            {EXEMPLE}
          </pre>
          <span className="flex items-center gap-1 text-micro text-zinc-500">
            Commande
            <InfoTip>
              La commande est lancée telle quelle, sans shell : une commande
              par service, et pas de{" "}
              <code className="text-zinc-300">&amp;&amp;</code>.
            </InfoTip>
          </span>
          {chemin ? (
            <a
              href={`vscode://file/${chemin.replace(/\\/g, "/")}/agents.json`}
              className="inline-block rounded border border-zinc-700 px-2 py-1 text-mini text-zinc-300 hover:border-zinc-500 hover:text-zinc-100"
            >
              Ouvrir agents.json
            </a>
          ) : null}
        </div>
      </details>
    </div>
  );
}
