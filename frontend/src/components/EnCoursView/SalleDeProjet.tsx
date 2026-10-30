import { useCallback, useMemo, useState } from "react";
import IconeDuProjet from "../ProjetsView/IconeDuProjet";
import { useApercuDuProjet } from "../../hooks/useApercuDesProjets";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import { IconExternal } from "../../design/icons";
import Agrandi from "../../design/bureau/Agrandi";
import CheminDeCables from "../../design/bureau/CheminDeCables";
import Climatiseur from "../../design/bureau/Climatiseur";
import BoucheVMC, { type RegimeVMC } from "../../design/bureau/BoucheVMC";
import Extincteur from "../../design/bureau/Extincteur";
import PorteCoupeFeu from "../../design/bureau/PorteCoupeFeu";
import type { ServiceActif } from "../../types/api";
import AgentsDeProduit, { type AgentDuService } from "./AgentsDeProduit";
import ArretDuProjet from "./ArretDuProjet";
import BaieAvecFiche from "./BaieAvecFiche";
import EcranMural from "./EcranMural";
import JournalDuService from "./JournalDuService";
import { baiesDuProjet } from "./baies";
import SolDeSalle from "./SolDeSalle";
import { formaterMo, type GroupeDeProjet } from "./format";

interface SalleDeProjetProps {
  groupe: GroupeDeProjet;
  /** Heure de la dernière lecture de l'inventaire : elle relance la lecture des services. */
  lueA: number;
  /** Les agents que le produit déclare, tous services confondus ; vide, personne. */
  agents: readonly AgentDuService[];
  enArret: boolean;
  onArreterProjet: () => void;
}

const AUCUN: ServiceActif[] = [];

/** La VMC tourne si un service tourne, plus vite avec la mémoire du projet (ADR-058). */
function regimeDeLaVMC(enCours: boolean, memoireMo: number): RegimeVMC {
  if (!enCours) return "arret";
  if (memoireMo < 200) return "lent";
  return memoireMo < 500 ? "moyen" : "rapide";
}

/**
 * La salle d'un projet lancé — tickets 672, 710 et 711. Une salle par projet, une
 * baie par service. Au mur, un écran par service lancé par l'IDE, qui montre sa
 * sortie ; un clic la déplie en journal. Le mobilier ne porte aucun état (ADR-058) :
 * seuls les voyants, les écrans et les agents rendent des données.
 */
export default function SalleDeProjet({ groupe, lueA, agents, enArret, onArreterProjet }: SalleDeProjetProps) {
  const fetcher = useMemo(
    () => () => api.services.list(groupe.project_id),
    // `lueA` change l'identité du fetcher exprès : c'est la clé de la requête.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [groupe.project_id, lueA],
  );
  const { data: services } = useResource<ServiceActif[]>(fetcher, AUCUN, {
    projet: groupe.project_id,
    ressource: "services",
  });
  const [deplie, setDeplie] = useState<string | null>(null);
  const baies = baiesDuProjet(groupe.apps, services);
  const ecrans = services.filter((s) => s.pid !== null);
  const tombe = baies.some((b) => b.etat === "echoue");
  // Chaque port garde le nom du service qui l'écoute : « :5196 » seul ne dit
  // pas si l'on ouvre le frontend ou le backend.
  const ports = groupe.apps
    .flatMap((app) => app.ports.map((port) => ({ port, service: app.nom })))
    .sort((a, b) => a.port - b.port);
  const journal = services.find((s) => s.nom === deplie);
  const apercu = useApercuDuProjet(groupe.project_id);
  const enMarche = baies.some((b) => b.etat === "en-cours");
  // Un service qui disparaît referme son journal, pour qu'il ne se rouvre pas
  // tout seul à son retour : état ajusté pendant le rendu, sans effet.
  if (deplie !== null && journal === undefined && services.length > 0) setDeplie(null);
  const fermer = useCallback(() => setDeplie(null), []);
  const avecJournal = new Set(ecrans.map((s) => s.nom));

  return (
    <article
      aria-label={`Salle ${groupe.project_name}`}
      data-salle-projet={groupe.project_id}
      data-tombe={tombe}
      className={`flex flex-col overflow-hidden rounded-lg border bg-(--sprite-salle-mur) ${tombe ? "border-red-800" : "border-zinc-800"}`}
    >
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-zinc-800 bg-zinc-900/60 px-3 py-2">
        <IconeDuProjet projet={apercu ?? { id: groupe.project_id, name: groupe.project_name, icon: false }} taille="titre" />
        <h3 className="text-sm font-semibold text-zinc-100">{groupe.project_name}</h3>
        <span className="text-xs text-zinc-400">
          {baies.length} service{baies.length > 1 ? "s" : ""} · {formaterMo(groupe.memoire_mo)}
        </span>
        <span className="ml-auto flex flex-wrap items-center gap-2">
          {ports.map(({ port, service }) => (
            <a
              key={port}
              href={`http://localhost:${port}`}
              target="_blank"
              rel="noreferrer"
              aria-label={`Ouvrir ${service} :${port}`}
              title={`Ouvrir ${service} :${port}`}
              className="flex items-center gap-1 rounded-sm px-2 py-1 text-xs text-zinc-300 ring-1 ring-zinc-700 hover:bg-zinc-800 hover:text-zinc-100"
            >
              {service} :{port}
              <IconExternal size={12} aria-hidden="true" />
            </a>
          ))}
          <ArretDuProjet groupe={groupe} enArret={enArret} onArreterProjet={onArreterProjet} court />
        </span>
      </header>
      <div data-mur="serveurs" className="relative px-6 pt-8">
        <div className="absolute inset-x-0 top-0">
          <CheminDeCables />
        </div>
        {ecrans.length > 0 && (
          <div
            data-murs-d-ecrans
            className="mx-auto grid max-w-5xl grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-x-6 gap-y-4"
          >
            {ecrans.map((service) => (
              <EcranMural
                key={service.nom}
                service={service}
                deplie={deplie === service.nom}
                onBasculer={() => setDeplie(deplie === service.nom ? null : service.nom)}
              />
            ))}
          </div>
        )}
        <div data-sol-mobilier className="mt-4 flex items-end justify-between gap-4 border-b-4 border-(--sprite-salle-plinthe)">
          <span className="flex items-end gap-4">
            <Agrandi>
              <Climatiseur />
            </Agrandi>
            {baies.map((baie) => (
              <BaieAvecFiche key={baie.nom} baie={baie} app={groupe.apps.find((a) => a.nom === baie.nom)} />
            ))}
          </span>
          <AgentsDeProduit
            projectId={groupe.project_id}
            agents={agents}
            aUnJournal={(service) => avecJournal.has(service)}
            onOuvrirService={setDeplie}
          />
          <span className="flex items-end gap-4">
            <span className="self-start" title={`Ventilation : ${formaterMo(groupe.memoire_mo)} en service`}>
              <Agrandi>
                <BoucheVMC regime={regimeDeLaVMC(enMarche, groupe.memoire_mo)} />
              </Agrandi>
            </span>
            <Agrandi>
              <Extincteur />
            </Agrandi>
            {/* La porte est à l'échelle d'une personne : plus haute qu'une baie. */}
            <Agrandi relatif={1.85}>
              <PorteCoupeFeu />
            </Agrandi>
          </span>
        </div>
      </div>
      <SolDeSalle />
      {journal && (
        <JournalDuService projectName={groupe.project_name} service={journal} onFermer={fermer} />
      )}
    </article>
  );
}
