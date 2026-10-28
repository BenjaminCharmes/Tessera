import { useMemo } from "react";
import Agrandi from "../../design/bureau/Agrandi";
import Boite from "../../design/bureau/Boite";
import type { StreamState } from "../../hooks/streamState";
import { useProjects } from "../../hooks/useProjects";
import { useResource } from "../../hooks/useResource";
import { api } from "../../lib/api";
import { boiteAuxLettres } from "../../lib/bureau/boiteAuxLettres";
import { boiteDepuisPr } from "../../lib/bureau/boiteDepuisPr";
import { lienDuDepot } from "../../lib/lienDuDepot";
import {
  libelleCourtDeLaBoite,
  libelleDeLaBoite,
} from "../../lib/bureau/libelleDeLaBoite";
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
function usePrDuTicket(
  projet: string,
  ticketId: string | null,
  pr: number | null,
): PRStatusEntry | null {
  const fetcher = useMemo(
    () =>
      ticketId
        ? () =>
            api.github
              .getPrStatuses(projet)
              .then(
                (liste) =>
                  liste.find(
                    (e) =>
                      e.ticket_id === ticketId &&
                      (pr === null || e.pr_number === pr),
                  ) ?? null,
              )
        : null,
    [projet, ticketId, pr],
  );
  return useResource<PRStatusEntry | null>(fetcher, null).data;
}

/**
 * La boîte aux lettres d'une pièce, au mur près de la porte : cinq états, la PR et son
 * état en toutes lettres en infobulle. La boîte ouvre la PR quand on connaît son URL ;
 * le numéro écrit à côté doublait l'infobulle et a disparu (ticket-627).
 */
export default function BoiteAuxLettres({
  projet,
  etat,
}: BoiteAuxLettresProps) {
  const depuisEvenements = boiteAuxLettres(etat);
  // `ticketId` n'est posé que par l'instantané ou un `queue_progress` : un run
  // seul, vu en direct, ne le porte que dans ses événements.
  const ticketId =
    etat.ticketId ??
    etat.ticketEvents.find((ev) => ev.ticket_id)?.ticket_id ??
    null;
  const entree = usePrDuTicket(projet, ticketId, depuisEvenements.pr);
  const boite =
    depuisEvenements.etat === "aucune"
      ? boiteDepuisPr(entree)
      : depuisEvenements;
  // `pr-statuses` ne connaît une PR qu'une fois son numéro écrit dans le ticket,
  // et la file est souvent déjà passée au suivant : l'URL se déduit alors du
  // dépôt du projet (ticket-627).
  const { projects } = useProjects();
  const depot = lienDuDepot(
    projects.find((p) => p.id === projet)?.github_remote,
  );
  const url =
    entree !== null && entree.pr_number === boite.pr
      ? entree.pr_url
      : depot !== null && boite.pr !== null
        ? `${depot}/pull/${boite.pr}`
        : null;

  return (
    <div data-boite={boite.etat} className="flex items-end">
      {/* La boîte elle-même mène à la PR quand on connaît son URL (ticket-622). */}
      <AvecInfobulle
        label={libelleDeLaBoite(boite)}
        className="block"
        infobulle={libelleCourtDeLaBoite(boite)}
        onActiver={
          url
            ? () => window.open(url, "_blank", "noopener,noreferrer")
            : undefined
        }
      >
        <Agrandi>
          <Boite etat={boite.etat} />
        </Agrandi>
      </AvecInfobulle>
    </div>
  );
}
