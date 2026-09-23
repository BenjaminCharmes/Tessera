import { useCallback, useMemo, useState } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import type { ServiceActif } from "../types/api";

/**
 * Les services d'un projet, et de quoi les démarrer ou les arrêter —
 * ticket-138.
 *
 * Un service n'est pas un run : il n'a ni ticket, ni étapes, ni verdict, et
 * il ne se termine pas tout seul (ADR-042). Il a donc son propre hook plutôt
 * qu'une place dans `useSupervision`, dont l'état est bâti sur des runs.
 *
 * La lecture passe par `useResource`, qui existe précisément pour ça : il
 * annule la réponse en vol au changement de projet — sans quoi la liste d'un
 * projet quitté s'afficherait sous le suivant — et ne fait aucun `setState`
 * synchrone dans un effet (ticket-123).
 */
export interface UseServicesResult {
  services: ServiceActif[];
  /** Au moins un service tourne. */
  enCours: boolean;
  /**
   * Au moins un service s'est arrêté seul avec un code non nul. C'est le cas
   * où l'on va chercher les logs : il doit se voir, pas disparaître.
   */
  enEchec: boolean;
  /**
   * `false` quand le projet ne déclare aucun service : pas de bouton.
   *
   * Vient de la **liste**, pas d'un message d'erreur (ticket-146). Déduire un
   * état du texte d'un 409 cassait en silence dès que ce texte changeait — et
   * surtout, on ne l'apprenait qu'après avoir cliqué : le bouton disparaissait
   * sous le curseur sans rien expliquer.
   */
  declare: boolean;
  erreur: string | null;
  demarrer: () => Promise<void>;
  arreter: () => Promise<void>;
  rafraichir: () => void;
}

const AUCUN: ServiceActif[] = [];

export function useServices(
  projectId: string | null,
  /**
   * Compteur d'évènements de service venu de la supervision. Il change quand
   * un service démarre ou meurt, et c'est ce qui fait relire la liste : sans
   * lui, un service mort resterait affiché « en cours » indéfiniment, et le
   * bouton proposerait « Arrêter » pour un processus disparu (ticket-145).
   */
  signal = 0,
): UseServicesResult {
  // L'identité du fetcher **est** la clé de la requête (voir `useResource`).
  const fetcher = useMemo(
    () => (projectId ? () => api.services.list(projectId) : null),
    // `signal` ne sert pas *dans* le fetcher, et la règle le signale à juste
    // titre. Il est là exprès : dans `useResource`, l'identité du fetcher
    // **est** la clé de la requête, donc en changer l'identité est le moyen
    // prévu de relire. La règle ne peut pas le savoir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projectId, signal],
  );
  const { data: lus, error: erreurDeLecture, refresh } = useResource<
    ServiceActif[]
  >(fetcher, AUCUN);

  // Ce qu'une action vient de produire, tant que la relecture n'a pas eu
  // lieu : sans ça, le bouton ne changerait d'état qu'au rafraîchissement
  // suivant et paraîtrait n'avoir rien fait.
  const [apresAction, setApresAction] = useState<{
    projectId: string | null;
    signal: number;
    liste: ServiceActif[] | null;
    erreur: string | null;
    declare: boolean;
  }>({
    projectId: null,
    signal: 0,
    liste: null,
    erreur: null,
    declare: true,
  });

  // Une relecture déclenchée par le canal l'emporte sur ce qu'une action a
  // laissé : c'est elle qui sait qu'un service vient de mourir.
  const local =
    apresAction.projectId === projectId && apresAction.signal === signal
      ? apresAction
      : { liste: null, erreur: null, declare: true };

  const demarrer = useCallback(async () => {
    if (!projectId) return;
    try {
      const { services: liste } = await api.services.start(projectId);
      setApresAction({ projectId, signal, liste, erreur: null, declare: true });
    } catch (exc: unknown) {
      const message =
        exc instanceof Error ? exc.message : "Lancement impossible";
      // Le 409 d'ADR-042 dit quoi écrire dans `agents.json` : le remplacer
      // par « erreur » renverrait lire le code.
      // Le bouton reste en place : l'erreur s'affiche en infobulle. Le faire
      // disparaître sur un échec était le défaut de ticket-146.
      setApresAction({
        projectId,
        signal,
        liste: null,
        erreur: message,
        declare: true,
      });
    }
  }, [projectId, signal]);

  const arreter = useCallback(async () => {
    if (!projectId) return;
    try {
      await api.services.stop(projectId);
      setApresAction({ projectId, signal, liste: AUCUN, erreur: null, declare: true });
      refresh();
    } catch (exc: unknown) {
      setApresAction({
        projectId,
        signal,
        liste: null,
        erreur: exc instanceof Error ? exc.message : "Arrêt impossible",
        declare: true,
      });
    }
  }, [projectId, signal, refresh]);

  const services = local.liste ?? lus;

  return {
    services,
    enCours: services.some((s) => s.en_cours),
    enEchec: services.some(
      (s) => !s.en_cours && (s.code_de_sortie ?? 0) !== 0,
    ),
    // Un projet sans service déclaré rend une liste vide : c'est ce qui
    // décide, dès le premier rendu, qu'il n'y a pas de bouton à afficher.
    declare: services.length > 0,
    erreur: local.erreur ?? erreurDeLecture,
    demarrer,
    arreter,
    rafraichir: refresh,
  };
}
