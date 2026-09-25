import { useState } from "react";
import { adressesDansLaSortie } from "./adresse";
import AdresseDuService from "./AdresseDuService";
import { classeDeLEtat, etatDuService } from "../../design/etatDuService";
import type { ServiceActif } from "../../types/api";

/**
 * Les services lancés, leur adresse et leur sortie — ticket-145.
 *
 * Séparés des runs : un service n'a ni ticket, ni tours, ni verdict, et ne se
 * termine pas tout seul. Déplier l'un d'eux montre ses dernières lignes,
 * comme sélectionner un run montre ses tokens.
 *
 * Les adresses viennent de la sortie elle-même — Vite et uvicorn les y
 * annoncent. Sans elles, on lance un serveur sans savoir où il écoute. Il y
 * en a souvent **deux** : une commande `concurrently` lance un back et un
 * front, et une seule adresse ne peut pas représenter les deux (ticket-154).
 */
interface ServicesLancesProps {
  services: ServiceActif[];
  sortieDe: (projectId: string, nom: string) => string[];
}

/**
 * Ce que le service a écrit : le direct s'il est arrivé, sinon ce que le
 * backend a gardé — ticket-148. Le canal ne rejoue pas l'historique, et un
 * service annonce son adresse dans ses deux premières secondes.
 */
function lignesDe(
  service: ServiceActif,
  sortieDe: (projectId: string, nom: string) => string[],
): string[] {
  const direct = sortieDe(service.project_id, service.nom);
  const gardees = service.sortie ?? [];
  return direct.length >= gardees.length ? direct : gardees;
}

export default function ServicesLances({
  services,
  sortieDe,
}: ServicesLancesProps) {
  // Un ensemble, pas un seul nom : un projet qui lance un backend **et** un
  // frontend veut voir les deux sorties en même temps. L'accordéon fermait
  // l'une en ouvrant l'autre (ticket-148).
  const [ouverts, setOuverts] = useState<ReadonlySet<string>>(new Set());
  const cle = (service: ServiceActif) => `${service.project_id}:${service.nom}`;

  function basculer(nom: string) {
    setOuverts((prec) => {
      const suivant = new Set(prec);
      if (!suivant.delete(nom)) suivant.add(nom);
      return suivant;
    });
  }

  return (
    <section
      aria-label="Services lancés"
      className="space-y-1.5 border-b border-zinc-800 px-3 py-2"
    >
      {services.map((service) => {
        const lignes = lignesDe(service, sortieDe);
        // Pas d'adresse pour un service arrêté : elle mènerait vers un
        // serveur qui n'écoute plus.
        const adresses = service.en_cours
          ? adressesDansLaSortie(lignes, window.location.origin)
          : [];
        const echoue = etatDuService(service) === "echoue";
        const ouvert = ouverts.has(cle(service));

        // Un bloc par service, sa sortie dedans : les blocs dépliés étaient
        // rendus après toutes les puces, donc loin du service auquel ils
        // appartenaient (ticket-155).
        return (
          <div key={cle(service)} className="rounded-sm bg-zinc-900/40">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 p-1">
              <button
                type="button"
                onClick={() => basculer(cle(service))}
                aria-pressed={ouvert}
                title={`${service.project_id} · pid ${service.pid ?? "—"}`}
                className={`rounded-sm px-2 py-0.5 text-micro transition-colors hover:brightness-125 ${classeDeLEtat(service)}`}
              >
                {service.nom}
                {echoue ? ` · code ${service.code_de_sortie}` : ""}
              </button>

              {adresses.map((adresse) => (
                <AdresseDuService key={adresse.url} {...adresse} />
              ))}
            </div>

            {ouvert ? (
              <div className="px-1 pb-1">
                {/* Le nom au-dessus du bloc : la supervision montre tous les
                    projets, donc deux services peuvent porter le même nom
                    (ticket-149). */}
                <p className="px-1 text-micro text-zinc-500">
                  {`${service.project_id} · ${service.nom}`}
                </p>
                <pre
                  aria-label={`Sortie de ${service.nom}`}
                  className="max-h-40 overflow-auto whitespace-pre-wrap rounded-sm bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400"
                >
                  {lignes.join("\n") || "Ce service n'a encore rien écrit."}
                </pre>
              </div>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
