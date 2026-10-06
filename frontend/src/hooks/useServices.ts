import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { useResource } from "./useResource";
import { useFenetreVisible } from "./useFenetreVisible";
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

/**
 * À quelle cadence on relit tant qu'un service tourne — ticket-149.
 *
 * ticket-145 avait écarté le minuteur au profit du canal, et l'argument
 * tenait. Mais il fait dépendre l'affichage d'un canal dont aucun test ne
 * peut prouver le bon fonctionnement, et à l'usage la sortie n'apparaissait
 * pas. Le minuteur ne bat **que** lorsqu'un service est en cours ; le canal
 * reste la voie rapide.
 */
const CADENCE_MS = 5000;

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

  const fenetreVisible = useFenetreVisible();

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
      await api.services.start(projectId);
      // Surtout pas figer cette réponse : elle décrit l'état à la
      // milliseconde du démarrage, où rien n'a encore été écrit. La garder
      // laissait « n'a encore rien écrit » indéfiniment (ticket-149). Seul le
      // serveur sait ce qui tourne ; on relit.
      setApresAction({
        projectId,
        signal,
        liste: null,
        erreur: null,
        declare: true,
      });
      refresh();
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
  }, [projectId, signal, refresh]);

  const arreter = useCallback(async () => {
    if (!projectId) return;
    try {
      await api.services.stop(projectId);
      // Surtout pas `liste: AUCUN` : une liste vide *parce qu'on vient
      // d'arrêter* se lisait comme « ce projet ne déclare aucun service »,
      // et le bouton disparaissait au profit du mode d'emploi (ticket-148).
      // « Rien de déclaré » et « rien qui tourne » sont deux choses
      // différentes ; seule la relecture sait laquelle est vraie.
      setApresAction({
        projectId,
        signal,
        liste: null,
        erreur: null,
        declare: true,
      });
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
  const enCours = services.some((service) => service.en_cours);

  useEffect(() => {
    // Rien en cours ou fenêtre cachée : pas de minuteur (ticket-356).
    if (!projectId || !enCours || !fenetreVisible) return;
    const minuteur = setInterval(refresh, CADENCE_MS);
    return () => clearInterval(minuteur);
  }, [projectId, enCours, refresh, fenetreVisible]);

  return {
    services,
    enCours,
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
