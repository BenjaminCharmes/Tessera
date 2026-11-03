import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { createWebSocket, wsUrl, type WsMessage } from "../../lib/ws";
import type { EtapeMiseEnLigne } from "../../types/api";
import { estTerminee, fusionner, lireEvenement } from "./etapes";

interface Etat {
  /** Les noms d'étape du plan lancé, dans l'ordre. */
  plan: string[];
  /** L'état lu par `GET …/provision`, sans rien écrire. */
  lues: EtapeMiseEnLigne[];
  /** Ce que les événements `provisioning_step` ont rapporté depuis le lancement. */
  evenements: EtapeMiseEnLigne[];
  enCours: boolean;
  erreur: string | null;
}

const INITIAL: Etat = { plan: [], lues: [], evenements: [], enCours: false, erreur: null };

export interface UseMiseEnLigne {
  etapes: EtapeMiseEnLigne[];
  /** Lancée et pas encore rendue : le bouton reste désactivé. */
  enCours: boolean;
  /** Un message court, quand le lancement a été refusé ou le suivi coupé. */
  erreur: string | null;
  /** Rend `true` quand la mise en ligne est partie, `false` si le lancement a été refusé. */
  demarrer: () => Promise<boolean>;
}

/** Le texte d'une erreur d'API, réduit à ce que l'utilisateur peut lire. */
export function messageCourt(erreur: unknown): string {
  const texte = erreur instanceof Error ? erreur.message : "";
  if (texte.startsWith("API 409")) return "Une mise en ligne est déjà en cours pour ce projet.";
  if (texte.startsWith("API 422")) {
    try {
      const { detail } = JSON.parse(texte.slice("API 422: ".length)) as { detail?: unknown };
      if (typeof detail === "string" && detail) return detail;
    } catch {
      // Corps illisible : le message générique suffit.
    }
  }
  return "La mise en ligne n'a pas pu démarrer.";
}

/**
 * Lance la mise en ligne d'un projet et en suit les étapes — ticket-472.
 *
 * L'ordre des étapes vient de la réponse du `POST`, leur état initial de
 * `GET …/provision`, puis chaque événement `provisioning_step` de la socket
 * d'observation (ADR-041) recouvre ce qui précède. La socket s'ouvre avant le
 * `POST` : le premier événement ne peut pas partir avant qu'on l'écoute.
 */
export function useMiseEnLigne(projectId: string): UseMiseEnLigne {
  const [etat, setEtat] = useState<Etat>(INITIAL);
  const socket = useRef<WebSocket | null>(null);

  const fermer = useCallback(() => {
    socket.current?.close();
    socket.current = null;
  }, []);

  useEffect(() => fermer, [fermer]);
  useEffect(() => {
    if (!etat.enCours) fermer();
  }, [etat.enCours, fermer]);

  const recevoir = useCallback(
    (message: WsMessage) => {
      const evenement = lireEvenement(message, projectId);
      if (evenement === null) return;
      setEtat((avant) => {
        const evenements = [...avant.evenements.filter((e) => e.step !== evenement.step), evenement];
        return { ...avant, evenements, enCours: avant.enCours && !estTerminee(avant.plan, evenements) };
      });
    },
    [projectId],
  );

  const lire = useCallback(() => {
    api.provisioning
      .read(projectId)
      .then((lues) => setEtat((avant) => ({ ...avant, lues })))
      // La lecture n'est qu'un point de départ : les événements disent déjà tout.
      .catch(() => undefined);
  }, [projectId]);

  const demarrer = useCallback(async () => {
    fermer();
    setEtat({ ...INITIAL, enCours: true });
    const ws = createWebSocket(wsUrl("/api/v1/orchestrator/observe"), {
      onMessage: recevoir,
      onClose: () => {
        // Seule la socket courante compte : un relancement a déjà remplacé celle-ci.
        if (socket.current !== ws) return;
        socket.current = null;
        setEtat((avant) =>
          avant.enCours
            ? { ...avant, enCours: false, erreur: "Le suivi s'est interrompu : relance pour relire l'état." }
            : avant,
        );
      },
    });
    socket.current = ws;
    try {
      const lancee = await api.provisioning.start(projectId);
      setEtat((avant) => ({
        ...avant,
        plan: lancee.steps,
        enCours: avant.enCours && !estTerminee(lancee.steps, avant.evenements),
      }));
      lire();
      return true;
    } catch (e) {
      fermer();
      setEtat({ ...INITIAL, erreur: messageCourt(e) });
      return false;
    }
  }, [projectId, fermer, recevoir, lire]);

  return {
    etapes: fusionner(etat.plan, etat.lues, etat.evenements),
    enCours: etat.enCours,
    erreur: etat.erreur,
    demarrer,
  };
}
