import { useMemo } from "react";
import { api } from "../../lib/api";
import { useResource } from "../../hooks/useResource";
import Agrandi from "../../design/bureau/Agrandi";
import BaieHaute from "../../design/bureau/BaieHaute";
import CheminDeCables from "../../design/bureau/CheminDeCables";
import Climatiseur from "../../design/bureau/Climatiseur";
import DallePerforee from "../../design/bureau/DallePerforee";
import Extincteur from "../../design/bureau/Extincteur";
import PorteCoupeFeu from "../../design/bureau/PorteCoupeFeu";
import type { AppEnCours, ServiceActif } from "../../types/api";
import type { AgentDeProduit } from "../../types/activiteProduit";
import AgentsDeProduit from "./AgentsDeProduit";
import { baiesDeLApp } from "./baies";
import { formaterHeure, formaterMo } from "./format";

interface SalleDAppProps {
  app: AppEnCours;
  /** Heure de la dernière lecture de l'inventaire : elle relance la lecture des services. */
  lueA: number;
  /** Les agents que le produit déclare pour cette app ; vide, la salle n'en dessine aucun. */
  agents: readonly AgentDeProduit[];
}

const AUCUN: ServiceActif[] = [];

function ports(app: AppEnCours): string {
  return app.ports.length === 0 ? "—" : app.ports.map((port) => `:${port}`).join(" ");
}

/**
 * La salle d'une app lancée — ticket-672. Le mur porte le chemin de câbles, le
 * climatiseur, une baie par service (son voyant dit l'état), l'extincteur et la
 * porte coupe-feu ; le sol est un faux plancher. Tout est mobilier fixe (ADR-058)
 * sauf les voyants et les agents, un par entrée du fichier d'activité du produit
 * (ticket-673) : sans fichier lu, personne.
 */
export default function SalleDApp({ app, lueA, agents }: SalleDAppProps) {
  // Relire à chaque lecture de l'inventaire : un service arrêté change de voyant.
  const fetcher = useMemo(
    () => () => api.services.list(app.project_id),
    // `lueA` change l'identité du fetcher exprès : c'est la clé de la requête.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [app.project_id, lueA],
  );
  const { data: services } = useResource<ServiceActif[]>(fetcher, AUCUN, {
    projet: app.project_id,
    ressource: "services",
  });
  const baies = baiesDeLApp(app, services);

  return (
    <aside
      aria-label={`Salle ${app.project_name} — ${app.nom}`}
      data-salle-app={app.pid}
      className="mb-3 overflow-hidden rounded-lg border border-zinc-800 bg-(--sprite-salle-mur)"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 px-3 pt-[5px] text-micro">
        <h3 className="uppercase tracking-wide text-zinc-300">
          {app.project_name} · {app.nom}
        </h3>
        <p className="flex gap-3 text-zinc-400">
          <span>Ports {ports(app)}</span>
          <span className="tabular-nums">{formaterMo(app.memoire_mo)}</span>
          <span>Démarrée à {formaterHeure(app.demarre_a)}</span>
        </p>
      </div>
      <ul className="flex flex-wrap gap-x-3 px-3 text-micro text-zinc-500">
        {baies.map((baie) => (
          <li key={baie.nom}>
            {baie.nom} — {baie.libelle}
          </li>
        ))}
      </ul>
      <div
        data-mur="serveurs"
        className="relative border-b-4 border-(--sprite-salle-plinthe) px-3 pt-8"
      >
        <div className="absolute inset-x-0 top-0">
          <CheminDeCables />
        </div>
        <div className="flex justify-center">
          <Agrandi>
            <div className="flex items-end gap-4">
              <Climatiseur />
              {baies.map((baie) => (
                <BaieHaute key={baie.nom} etat={baie.etat} />
              ))}
              <Extincteur />
              <PorteCoupeFeu />
            </div>
          </Agrandi>
        </div>
      </div>
      <AgentsDeProduit projectId={app.project_id} agents={agents} />
      <div data-sol="dalles" className="sol-dalles flex h-14 items-center justify-center gap-20">
        <DallePerforee />
        <DallePerforee />
        <DallePerforee />
      </div>
    </aside>
  );
}
