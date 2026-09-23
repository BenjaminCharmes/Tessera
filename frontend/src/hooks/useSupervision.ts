import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl } from "../lib/ws";
import { INITIAL, applyEvent } from "./streamState";
import type { StreamState } from "./streamState";
import {
  LIGNES_GARDEES,
  cleDuService,
  majDesRuns,
} from "./supervisionEvents";
import type { OrchestratorEvent, RunActif } from "../types/api";

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
 * Pas de store global ni de Context : les deux consommateurs sont des enfants
 * directs d'`App`, donc un passage par props suffit, et ADR-013 reste tenu
 * sans exception à justifier.
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
  /** Les dernières lignes écrites par un service lancé (ticket-145). */
  sortieDuService: (projectId: string, nom: string) => string[];
  /**
   * Combien d'évènements de service ont été reçus. `useServices` s'en sert
   * pour relire la liste : sans ce signal, rien ne lui dirait qu'un service
   * vient de mourir, et le bouton proposerait « Arrêter » pour un processus
   * disparu.
   */
  signalServices: number;
}

const VIDE: StreamState = INITIAL;

export function useSupervision(): UseSupervisionResult {
  const [runs, setRuns] = useState<RunActif[]>([]);
  const [etats, setEtats] = useState<Record<string, StreamState>>({});
  const [selection, setSelection] = useState<string | null>(null);
  const [connecte, setConnecte] = useState(false);
  const [sorties, setSorties] = useState<Record<string, string[]>>({});
  const [signalServices, setSignalServices] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const abonnementRef = useRef<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl("/api/v1/orchestrator/observe"));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnecte(true);
      // Se rattacher ne relance rien depuis ticket-128 : la socket observe,
      // elle ne commande pas. C'est ce qui rend la reconnexion sûre.
      if (abonnementRef.current) {
        ws.send(JSON.stringify({ subscribe: abonnementRef.current }));
      }
    };

    ws.onmessage = (message: MessageEvent) => {
      try {
        const brut = JSON.parse(message.data as string) as OrchestratorEvent & {
          runs?: RunActif[];
        };

        if ((brut.type as string) === "snapshot") {
          setRuns(brut.runs ?? []);
          return;
        }

        // Les évènements de service n'ont pas de `run_id` : les laisser
        // tomber dans le test ci-dessous jetait leur sortie avant même
        // qu'on ait écrit de quoi l'afficher (ticket-145).
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

        setEtats((prec) => ({
          ...prec,
          [runId]: applyEvent(prec[runId] ?? INITIAL, brut),
        }));

        // `run_closed` est le seul événement publié après la libération du
        // projet : c'est lui, et pas `pipeline_done`, qui retire la carte.
        if (brut.type === "run_closed") {
          setRuns((prec) => prec.filter((r) => r.run_id !== runId));
          return;
        }
        setRuns((prec) => majDesRuns(prec, brut, runId));
      } catch {
        // trame malformée : l'ignorer vaut mieux que casser l'affichage
      }
    };

    ws.onclose = () => setConnecte(false);

    return () => {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onclose = null;
      ws.close();
      wsRef.current = null;
    };
  }, []);

  const selectionner = useCallback((runId: string | null) => {
    const ws = wsRef.current;
    const precedent = abonnementRef.current;
    abonnementRef.current = runId;
    setSelection(runId);
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    // Se désabonner du précédent : sans cela, le flux de tokens de tous les
    // runs déjà regardés continuerait d'arriver, ce que l'abonnement existe
    // précisément pour éviter.
    if (precedent) ws.send(JSON.stringify({ unsubscribe: precedent }));
    if (runId) ws.send(JSON.stringify({ subscribe: runId }));
  }, []);

  const etatDe = useCallback(
    (runId: string): StreamState => etats[runId] ?? VIDE,
    [etats],
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
    // Le POST repond avant le premier evenement du run : sans cette entree,
    // la carte n'apparaitrait qu'au premier `agent_started`, et le bouton
    // semblerait n'avoir rien fait.
    setRuns((prec) =>
      prec.some((r) => r.run_id === run.run_id) ? prec : [...prec, run],
    );
  }, []);

  return {
    runs,
    selection,
    selectionner,
    etatDe,
    connecte,
    envoyer,
    suivre,
    sortieDuService,
    signalServices,
  };
}
