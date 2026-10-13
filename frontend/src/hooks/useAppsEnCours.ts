import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useFenetreVisible } from "./useFenetreVisible";
import type { AppEnCours } from "../types/api";

/** À quelle cadence on relit l'inventaire — ticket-417. */
export const CADENCE_APPS_MS = 10_000;

export interface UseAppsEnCoursResult {
  /** `null` tant que la première lecture n'est pas revenue. */
  apps: AppEnCours[] | null;
  /** Heure de la dernière lecture réussie, pour les durées affichées. */
  lueA: number;
  /** Dernière erreur de lecture ou d'arrêt ; `null` quand tout va bien. */
  erreur: string | null;
  /** Arrête l'app de ce pid, puis relit l'inventaire. */
  arreter: (pid: number) => Promise<void>;
  rafraichir: () => void;
}

function message(exc: unknown, defaut: string): string {
  return exc instanceof Error ? exc.message : defaut;
}

/**
 * Les apps de projet vivantes sur la machine — ticket-417.
 *
 * Il vit au niveau du cockpit, pas dans la vue : la pastille de la barre de
 * navigation doit compter les apps même quand la vue n'est pas ouverte. Le
 * minuteur se suspend quand la fenêtre est cachée (ticket-356). La donnée
 * précédente reste affichée pendant une relecture, et en cas d'erreur.
 */
export function useAppsEnCours(): UseAppsEnCoursResult {
  const [apps, setApps] = useState<AppEnCours[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [lueA, setLueA] = useState(() => Date.now());
  const [tick, setTick] = useState(0);
  const fenetreVisible = useFenetreVisible();

  useEffect(() => {
    let annule = false;
    api.services
      .running()
      .then((lues) => {
        if (annule) return;
        setApps(lues);
        setLueA(Date.now());
        setErreur(null);
      })
      .catch((exc: unknown) => {
        if (!annule) setErreur(message(exc, "Lecture impossible"));
      });
    return () => {
      annule = true;
    };
  }, [tick]);

  useEffect(() => {
    if (!fenetreVisible) return;
    const minuteur = setInterval(() => setTick((t) => t + 1), CADENCE_APPS_MS);
    return () => clearInterval(minuteur);
  }, [fenetreVisible]);

  const rafraichir = useCallback(() => setTick((t) => t + 1), []);

  const arreter = useCallback(
    async (pid: number) => {
      try {
        await api.services.stopRunning(pid);
      } catch (exc: unknown) {
        setErreur(message(exc, "Arrêt impossible"));
        return;
      }
      rafraichir();
    },
    [rafraichir],
  );

  return { apps, lueA, erreur, arreter, rafraichir };
}
