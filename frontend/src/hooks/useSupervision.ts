import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl } from "../lib/ws";
import { INITIAL, applyEvent, etatDepuisRun } from "./streamState";
import type { StreamState } from "./streamState";
import { LIGNES_GARDEES, cleDuService, majDesRuns } from "./supervisionEvents";
import { abonnementsVoulus, diffDesAbonnements } from "./abonnements";
import type { SlotsDAbonnement } from "./abonnements";
import type { OrchestratorEvent, RunActif, RunEvent } from "../types/api";
import { api } from "../lib/api";
import { runStore } from "./runStore";

/** Lance une RAF en navigateur, un setTimeout(16) hors navigateur (ticket-353). */
function scheduleRaf(fn: () => void): number {
  if (typeof requestAnimationFrame !== "undefined") {
    return requestAnimationFrame(fn);
  }
  return setTimeout(fn, 16) as unknown as number;
}

/** Annule une RAF ou un setTimeout lancé par scheduleRaf. */
function cancelRaf(id: number): void {
  if (typeof cancelAnimationFrame !== "undefined") {
    cancelAnimationFrame(id);
  } else {
    clearTimeout(id);
  }
}

/**
 * Tous les runs de la machine, sur une seule socket — ticket-129.
 *
 * Remplace `useOrchestratorStream`, qui ouvrait une socket **par projet** et
 * la fermait en changeant de projet : ce qui tournait ailleurs devenait
 * invisible. ADR-038 autorise un run par projet et N projets en parallèle,
 * et c'est ce parallélisme que l'IDE ne montrait pas.
 *
 * Un seul `useSupervision` est monté, dans `App`. Ses deux sorties servent
 * deux besoins : `runs` alimente la vue de supervision, `stream` garde
 * l'interface que `AgentPanel`, `RunView` et la sidebar attendent déjà — un
 * seul projet, celui qui est actif.
 *
 * Les états de run vivent dans `runStore` (store externe, ticket-354) :
 * un événement d'un run ne redessine que les composants qui l'affichent.
 */
export interface UseSupervisionResult {
  /** Les runs vivants, tous projets confondus. */
  runs: RunActif[];
  /** Le run dont on regarde le détail, et dont on reçoit les tokens. */
  selection: string | null;
  selectionner: (runId: string | null) => void;
  /** L'état accumulé d'un run, pour l'afficher sans le rejouer. */
  etatDe: (runId: string) => StreamState;
  /** Vrai quand la socket d'observation est ouverte. */
  connecte: boolean;
  /** Adresse un message de dialogue au run nomme (ADR-025). */
  envoyer: (runId: string, payload: Record<string, string>) => void;
  /** Enregistre un run qu'on vient de lancer, avant son premier evenement. */
  suivre: (run: RunActif) => void;
  /**
   * Déclare le run dont une vue affiche le texte (ticket-183).
   *
   * Sans elle, seul un lancement ou un clic dans Supervision abonnait la
   * socket : une page rechargée voyait les transitions d'un run et jamais son
   * travail.
   */
  observerLeTexte: (runId: string | null) => void;
  /** Les dernières lignes écrites par un service lancé (ticket-145). */
  sortieDuService: (projectId: string, nom: string) => string[];
  /**
   * Combien d'évènements de service ont été reçus. `useServices` s'en sert
   * pour relire la liste : sans ce signal, rien ne lui dirait qu'un service
   * vient de mourir, et le bouton proposerait « Arrêter » pour un processus
   * disparu.
   */
  signalServices: number;
  /**
   * Retire un run clos de la liste des cartes (ticket-267).
   *
   * `run_closed` marque le run comme terminé (`runClosed: true`) mais ne le
   * retire pas automatiquement : c'est l'utilisateur qui ferme via le bouton
   * « Fermer » de l'AgentPanel, après avoir vu le résumé final.
   */
  fermerRun: (runId: string) => void;
  /**
   * Retire plusieurs runs clos en une seule mise à jour d'état (ticket-344).
   * `fermerRun` reste disponible pour la fermeture unitaire depuis AgentPanel.
   */
  fermerRuns: (runIds: string[]) => void;
}

const VIDE: StreamState = INITIAL;

export function useSupervision(): UseSupervisionResult {
  const [runs, setRuns] = useState<RunActif[]>([]);
  const [selection, setSelection] = useState<string | null>(null);
  const [connecte, setConnecte] = useState(false);
  const [sorties, setSorties] = useState<Record<string, string[]>>({});
  const [signalServices, setSignalServices] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  // Qui demande quoi, et ce que la socket porte déjà. Deux slots, parce que
  // deux vues veulent du texte : l'onglet Supervision et le panneau du projet
  // actif (ticket-183).
  const slotsRef = useRef<SlotsDAbonnement>({ selection: null, panneau: null });
  const abonnesRef = useRef<Set<string>>(new Set());
  // Rechargement de page (ticket-325) : runs dont l'historique a été chargé.
  const historyLoadedRef = useRef<Set<string>>(new Set());
  // Événements en direct reçus pendant qu'on attend le chargement de l'historique.
  const historyBufferRef = useRef<Record<string, OrchestratorEvent[]>>({});
  // Regroupement par image : événements reçus mais pas encore appliqués (ticket-353).
  const pendingRef = useRef<OrchestratorEvent[]>([]);
  const rafIdRef = useRef<number | null>(null);

  /**
   * Applique tous les événements en attente : met à jour le store externe
   * (ticket-354) et setRuns (hors agent_token qui n'affecte pas la liste).
   *
   * Appelé soit par la RAF planifiée, soit en avance par le handler de snapshot.
   * setRuns est stable (contrat React useState) : useCallback([]) est correct.
   */
  const flush = useCallback(() => {
    rafIdRef.current = null;
    const batch = pendingRef.current.splice(0);
    if (batch.length === 0) return;
    // Mettre à jour le store externe en une passe (ticket-354).
    runStore.appliquer(batch);
    // Mettre à jour la liste des runs (hors tokens qui ne changent rien).
    setRuns((prec) => {
      let liste = prec;
      for (const ev of batch) {
        if (!ev.run_id || ev.type === "agent_token") continue;
        liste = majDesRuns(liste, ev, ev.run_id);
      }
      return liste;
    });
  }, []); // setRuns, runStore.appliquer et majDesRuns sont stables

  /** Programme un flush si aucun n'est déjà planifié (ticket-353). */
  const scheduleFlush = useCallback(() => {
    if (rafIdRef.current !== null) return;
    rafIdRef.current = scheduleRaf(flush);
  }, [flush]); // flush est stable

  /** Met la socket à jour sur ce que les slots demandent. */
  const majDesAbonnements = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const voulus = abonnementsVoulus(slotsRef.current);
    const { ajouts, retraits } = diffDesAbonnements(abonnesRef.current, voulus);
    for (const run of retraits) ws.send(JSON.stringify({ unsubscribe: run }));
    for (const run of ajouts) {
      ws.send(JSON.stringify({ subscribe: run }));
      // Vider les tokens avant le rejeu : le backend renvoie le texte à chaque
      // abonnement, et les ajouter à l'état déjà accumulé doublerait le texte
      // visible (ticket-313). runStore.clearTokens lit directement le store.
      runStore.clearTokens(run);
    }
    abonnesRef.current = voulus;
  }, []); // runStore.clearTokens est stable

  useEffect(() => {
    // La socket se rouvre : un redémarrage du backend suffisait à rendre
    // l'onglet aveugle définitivement, et le seul signe était une étiquette
    // « hors ligne » (ticket-163). Le délai croît puis plafonne, pour ne pas
    // marteler un backend éteint.
    let vivant = true;
    let essais = 0;
    let minuteur: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket;

    const ouvrir = () => {
      ws = new WebSocket(wsUrl("/api/v1/orchestrator/observe"));
      wsRef.current = ws;
      brancher(ws);
    };

    const replanifier = () => {
      if (!vivant) return;
      const delai = Math.min(500 * 2 ** essais, 15_000);
      essais += 1;
      minuteur = setTimeout(ouvrir, delai);
    };

    /**
     * Charge les événements persistés d'un run vivant et les rejoue dans
     * le store — ticket-325.
     */
    const chargerHistorique = async (runId: string, dbRunId: string) => {
      try {
        const evts: RunEvent[] = await api.runs.events(dbRunId);
        const dernierTs = evts.length > 0 ? evts[evts.length - 1].timestamp : null;
        let etat: StreamState = INITIAL;
        for (const ev of evts) {
          etat = applyEvent(etat, {
            ...ev,
            ticket_id: "",
            run_id: runId,
          } as OrchestratorEvent);
        }
        for (const ev of historyBufferRef.current[runId] ?? []) {
          if (!dernierTs || ev.timestamp > dernierTs) {
            etat = applyEvent(etat, ev);
          }
        }
        runStore.set(runId, etat);
      } catch {
        // Historique indisponible : vider le tampon sur l'état courant.
        let etat = runStore.getSnapshot()[runId] ?? INITIAL;
        for (const ev of historyBufferRef.current[runId] ?? []) {
          etat = applyEvent(etat, ev);
        }
        runStore.set(runId, etat);
      } finally {
        historyLoadedRef.current.add(runId);
        delete historyBufferRef.current[runId];
      }
    };

    const brancher = (ws: WebSocket) => {
      ws.onopen = () => {
        essais = 0;
        setConnecte(true);
        // Se rattacher ne relance rien depuis ticket-128 : la socket observe,
        // elle ne commande pas. C'est ce qui rend la reconnexion sûre. La
        // nouvelle socket repart vierge côté serveur : tout se redemande.
        abonnesRef.current = new Set();
        majDesAbonnements();
      };

      ws.onmessage = (message: MessageEvent) => {
        try {
          const brut = JSON.parse(
            message.data as string,
          ) as OrchestratorEvent & {
            runs?: RunActif[];
          };

          if ((brut.type as string) === "snapshot") {
            // Vider la file en attente avant l'instantané (ticket-353).
            flush();
            const recus = brut.runs ?? [];
            setRuns(recus);
            // Semer l'état dans le store : `agent_started` ne repassera pas,
            // et sans lui le panneau resterait au repos pour toute la durée
            // du run (ticket-163).
            const snapshot = runStore.getSnapshot();
            for (const r of recus) {
              if (!snapshot[r.run_id]) {
                runStore.set(r.run_id, etatDepuisRun(r));
              }
            }
            // Ticket-325 : charger l'historique pour les runs vivants.
            for (const r of recus) {
              if (r.db_run_id && !historyLoadedRef.current.has(r.run_id)) {
                historyBufferRef.current[r.run_id] = [];
                void chargerHistorique(r.run_id, r.db_run_id);
              }
            }
            return;
          }

          // Les évènements de service n'ont pas de `run_id`.
          const type = brut.type as string;
          if (type === "service_output" || type === "service_closed") {
            const nom = String(
              (brut.data as Record<string, unknown>)?.["service"] ?? "",
            );
            const ligne = (brut.data as Record<string, unknown>)?.["ligne"];
            if (brut.project_id && nom && typeof ligne === "string") {
              const cle = cleDuService(brut.project_id, nom);
              setSorties((prec) => ({
                ...prec,
                [cle]: [...(prec[cle] ?? []), ligne].slice(-LIGNES_GARDEES),
              }));
            }
            setSignalServices((n) => n + 1);
            return;
          }

          const runId = brut.run_id;
          if (!runId) return;

          // Ticket-325 : si l'historique est en cours de chargement, mettre
          // l'événement en tampon plutôt que de l'appliquer immédiatement.
          if (runId in historyBufferRef.current) {
            historyBufferRef.current[runId]!.push(brut);
            // Tokens ignorés ici aussi : ils ne changent rien dans la liste.
            if (brut.type !== "agent_token") {
              setRuns((prec) => majDesRuns(prec, brut, runId));
            }
            return;
          }

          // Regroupement par image : mise en file + RAF (ticket-353).
          pendingRef.current.push(brut);
          scheduleFlush();
        } catch {
          // trame malformée : l'ignorer vaut mieux que casser l'affichage
        }
      };

      ws.onclose = () => {
        setConnecte(false);
        replanifier();
      };
    };

    ouvrir();

    return () => {
      vivant = false;
      if (minuteur !== null) clearTimeout(minuteur);
      // Annuler le flush planifié (ticket-353).
      if (rafIdRef.current !== null) {
        cancelRaf(rafIdRef.current);
        rafIdRef.current = null;
      }
      ws.onopen = null;
      ws.onmessage = null;
      ws.onclose = null;
      ws.close();
      wsRef.current = null;
    };
  }, [majDesAbonnements, flush, scheduleFlush]);

  const selectionner = useCallback(
    (runId: string | null) => {
      slotsRef.current = { ...slotsRef.current, selection: runId };
      setSelection(runId);
      majDesAbonnements();
    },
    [majDesAbonnements],
  );

  const observerLeTexte = useCallback(
    (runId: string | null) => {
      if (slotsRef.current.panneau === runId) return;
      slotsRef.current = { ...slotsRef.current, panneau: runId };
      majDesAbonnements();
    },
    [majDesAbonnements],
  );

  /**
   * Lit l'état d'un run depuis le store externe (ticket-354).
   *
   * Identité stable : ne change pas quand un autre run reçoit un événement.
   * L'état retourné est toujours celui du store au moment de l'appel.
   */
  const etatDe = useCallback(
    (runId: string): StreamState => runStore.getSnapshot()[runId] ?? VIDE,
    [], // stable — lit depuis le store, pas depuis un state React
  );

  const envoyer = useCallback(
    (runId: string, payload: Record<string, string>) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ ...payload, run_id: runId }));
      }
    },
    [],
  );

  const sortieDuService = useCallback(
    (projectId: string, nom: string): string[] =>
      sorties[cleDuService(projectId, nom)] ?? [],
    [sorties],
  );

  const suivre = useCallback((run: RunActif) => {
    setRuns((prec) =>
      prec.some((r) => r.run_id === run.run_id) ? prec : [...prec, run],
    );
  }, []);

  const fermerRun = useCallback((runId: string) => {
    setRuns((prec) => prec.filter((r) => r.run_id !== runId));
  }, []);

  const fermerRuns = useCallback((runIds: string[]) => {
    const ids = new Set(runIds);
    setRuns((prec) => prec.filter((r) => !ids.has(r.run_id)));
  }, []);

  return {
    runs,
    selection,
    selectionner,
    etatDe,
    connecte,
    envoyer,
    suivre,
    observerLeTexte,
    sortieDuService,
    signalServices,
    fermerRun,
    fermerRuns,
  };
}

