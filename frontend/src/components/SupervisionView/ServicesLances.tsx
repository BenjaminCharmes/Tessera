import { useState } from "react";
import { adresseDansLaSortie } from "./adresse";
import { classeDeLEtat, etatDuService } from "../../design/etatDuService";
import type { ServiceActif } from "../../types/api";

/**
 * Les services lancés, leur adresse et leur sortie — ticket-145.
 *
 * Séparés des runs : un service n'a ni ticket, ni tours, ni verdict, et ne se
 * termine pas tout seul. Déplier l'un d'eux montre ses dernières lignes,
 * comme sélectionner un run montre ses tokens.
 *
 * L'adresse vient de la sortie elle-même — Vite et uvicorn l'y annoncent.
 * Sans elle, on lance un serveur sans savoir où il écoute.
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
      className="border-b border-zinc-800 px-3 py-2"
    >
      <div className="flex flex-wrap items-center gap-2">
        {services.map((service) => {
          const lignes = lignesDe(service, sortieDe);
          // Pas d'adresse pour un service arrêté : elle mènerait vers un
          // serveur qui n'écoute plus.
          const adresse = service.en_cours ? adresseDansLaSortie(lignes) : null;
          const echoue = etatDuService(service) === "echoue";
          return (
            <span key={cle(service)} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => basculer(cle(service))}
                aria-pressed={ouverts.has(cle(service))}
                title={`${service.project_id} · pid ${service.pid ?? "—"}`}
                className={`rounded-sm px-2 py-0.5 text-micro transition-colors hover:brightness-125 ${classeDeLEtat(service)}`}
              >
                {service.nom}
                {echoue ? ` · code ${service.code_de_sortie}` : ""}
              </button>
              {adresse ? (
                <a
                  href={adresse}
                  target="_blank"
                  rel="noreferrer"
                  className="text-micro text-zinc-400 underline decoration-dotted hover:text-zinc-200"
                >
                  {adresse}
                </a>
              ) : null}
            </span>
          );
        })}
      </div>

      {services
        .filter((service) => ouverts.has(cle(service)))
        .map((service) => (
          <pre
            key={cle(service)}
            aria-label={`Sortie de ${service.nom}`}
            className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-sm bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400"
          >
            {lignesDe(service, sortieDe).join("\n") ||
              "Ce service n'a encore rien écrit."}
          </pre>
        ))}
    </section>
  );
}
