import { useState } from "react";
import { adresseDansLaSortie } from "./adresse";
import type { ServiceActif } from "../../types/api";

/**
 * Les services lancés, leur adresse et leur sortie — ticket-145.
 *
 * Séparés des runs : un service n'a ni ticket, ni tours, ni verdict, et ne se
 * termine pas tout seul. Sélectionner l'un d'eux montre ses dernières lignes,
 * comme sélectionner un run montre ses tokens.
 *
 * L'adresse vient de la sortie elle-même — Vite et uvicorn l'y annoncent.
 * Sans elle, on lance un serveur sans savoir où il écoute.
 */
interface ServicesLancesProps {
  services: ServiceActif[];
  sortieDe: (projectId: string, nom: string) => string[];
}

export default function ServicesLances({
  services,
  sortieDe,
}: ServicesLancesProps) {
  const [ouvert, setOuvert] = useState<string | null>(null);
  const cle = (s: ServiceActif) => `${s.project_id}:${s.nom}`;
  const selectionne = services.find((s) => cle(s) === ouvert) ?? null;
  const lignes = selectionne
    ? sortieDe(selectionne.project_id, selectionne.nom)
    : [];

  return (
    <section
      aria-label="Services lancés"
      className="border-b border-zinc-800 px-3 py-2"
    >
      <div className="flex flex-wrap items-center gap-2">
        {services.map((service) => {
          const sortie = sortieDe(service.project_id, service.nom);
          const adresse = service.en_cours
            ? adresseDansLaSortie(sortie)
            : null;
          const echoue = !service.en_cours && (service.code_de_sortie ?? 0) !== 0;
          return (
            <span key={cle(service)} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() =>
                  setOuvert((prec) => (prec === cle(service) ? null : cle(service)))
                }
                aria-pressed={ouvert === cle(service)}
                title={`${service.project_id} · pid ${service.pid}`}
                className={`rounded-sm px-2 py-0.5 text-micro transition-colors ${
                  service.en_cours
                    ? "bg-blue-500/20 text-blue-200 hover:bg-blue-500/30"
                    : echoue
                      ? "bg-red-500/20 text-red-200 hover:bg-red-500/30"
                      : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                }`}
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

      {selectionne ? (
        <pre
          aria-label={`Sortie de ${selectionne.nom}`}
          className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-sm bg-zinc-950 p-2 text-micro leading-relaxed text-zinc-400"
        >
          {lignes.length > 0
            ? lignes.join("\n")
            : "Ce service n'a encore rien écrit."}
        </pre>
      ) : null}
    </section>
  );
}
