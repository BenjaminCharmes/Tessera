import { useMemo } from "react";
import Boite from "../../design/bureau/Boite";
import type { StreamState } from "../../hooks/streamState";
import { useResource } from "../../hooks/useResource";
import { api } from "../../lib/api";
import { boiteAuxLettres } from "../../lib/bureau/boiteAuxLettres";
import { boiteDepuisPr } from "../../lib/bureau/boiteDepuisPr";
import { libelleCourtDeLaBoite, libelleDeLaBoite } from "../../lib/bureau/libelleDeLaBoite";
import type { PRStatusEntry } from "../../types/api";
import AvecInfobulle from "./AvecInfobulle";

interface BoiteAuxLettresProps {
  projet: string;
  etat: StreamState;
}

/**
 * La PR du ticket en cours, lue dans `pr-statuses` : elle donne l'URL du lien,
 * et l'état quand les événements du run ne sont plus là (rechargement).
 * Une seule lecture, sans minuteur : les événements prennent le relais.
 */
function usePrDuTicket(projet: string, ticketId: string | null, pr: number | null): PRStatusEntry | null {
  const fetcher = useMemo(
    () =>
      ticketId
        ? () =>
            api.github
              .getPrStatuses(projet)
              .then(
                (liste) =>
                  liste.find((e) => e.ticket_id === ticketId && (pr === null || e.pr_number === pr)) ?? null,
              )
        : null,
    [projet, ticketId, pr],
  );
  return useResource<PRStatusEntry | null>(fetcher, null).data;
}

/**
 * La boîte aux lettres d'une pièce, au mur près de la porte : cinq états, le numéro
 * de PR lié à son URL quand on la connaît, l'état en toutes lettres en infobulle.
 */
export default function BoiteAuxLettres({ projet, etat }: BoiteAuxLettresProps) {
  const depuisEvenements = boiteAuxLettres(etat);
  // `ticketId` n'est posé que par l'instantané ou un `queue_progress` : un run
  // seul, vu en direct, ne le porte que dans ses événements.
  const ticketId = etat.ticketId ?? etat.ticketEvents.find((ev) => ev.ticket_id)?.ticket_id ?? null;
  const entree = usePrDuTicket(projet, ticketId, depuisEvenements.pr);
  const boite = depuisEvenements.etat === "aucune" ? boiteDepuisPr(entree) : depuisEvenements;
  const url = entree !== null && entree.pr_number === boite.pr ? entree.pr_url : null;

  return (
    <div data-boite={boite.etat} className="flex items-end gap-1">
      <AvecInfobulle label={libelleDeLaBoite(boite)} className="block" infobulle={libelleCourtDeLaBoite(boite)}>
        <Boite etat={boite.etat} />
      </AvecInfobulle>
      {boite.pr !== null &&
          (url ? (
            <a href={url} target="_blank" rel="noreferrer" className="text-micro text-blue-300 hover:underline">
              #{boite.pr}
            </a>
          ) : (
            <span className="text-micro text-zinc-400">#{boite.pr}</span>
          ))}
    </div>
  );
}
