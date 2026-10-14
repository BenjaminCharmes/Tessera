import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useFenetreVisible } from "./useFenetreVisible";
import {
  ajouter,
  cleArret,
  cleLancement,
  DELAI_ATTENTE_MS,
  retirer,
  trierAttentes,
  type Attentes,
} from "./enAttente";
import type { AppEnCours } from "../types/api";

/** À quelle cadence on relit l'inventaire — ticket-417. */
export const CADENCE_APPS_MS = 10_000;
/** Tant qu'un arrêt ou un lancement est attendu — ticket-424. */
export const CADENCE_ATTENTE_MS = 2_000;

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
  /** Arrête toutes les apps du projet : ses services, puis chaque app externe. */
  arreterProjet: (projectId: string, apps: AppEnCours[]) => Promise<void>;
  /** Lance les services déclarés du projet. */
  lancer: (projectId: string) => Promise<void>;
  /** Ce pid a reçu l'ordre d'arrêt et figure encore dans l'inventaire. */
  enArret: (pid: number) => boolean;
  /** Ce projet a reçu l'ordre de lancement et n'est pas encore revenu. */
  enLancement: (projectId: string) => boolean;
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
  const [echec, setEchec] = useState<string | null>(null);
  const [lueA, setLueA] = useState(() => Date.now());
  const [tick, setTick] = useState(0);
  const [attentes, setAttentes] = useState<Attentes>({});
  // La référence est la source des opérations en attente ; l'état n'en est que
  // le miroir pour l'affichage, et la lecture qui revient y voit le dernier clic.
  const attentesRef = useRef<Attentes>({});
  const appsRef = useRef<AppEnCours[]>([]);
  const fenetreVisible = useFenetreVisible();
  const enAttente = Object.keys(attentes).length > 0;

  const changerAttentes = useCallback((suite: Attentes) => {
    attentesRef.current = suite;
    setAttentes(suite);
  }, []);

  // À chaque lecture, réussie ou non : lever ce qui est résolu, abandonner ce
  // qui traîne. Sur un échec de lecture, on juge sur la dernière liste connue.
  const solder = useCallback(
    (vues: AppEnCours[]) => {
      const avant = attentesRef.current;
      const { restantes, expirees } = trierAttentes(avant, vues, Date.now());
      if (Object.keys(restantes).length === Object.keys(avant).length) return;
      changerAttentes(restantes);
      if (expirees.length > 0) {
        setEchec(`Sans effet après ${DELAI_ATTENTE_MS / 1000} s : l'opération a été abandonnée`);
      }
    },
    [changerAttentes],
  );

  useEffect(() => {
    let annule = false;
    api.services
      .running()
      .then((lues) => {
        if (annule) return;
        appsRef.current = lues;
        setApps(lues);
        setLueA(Date.now());
        setErreur(null);
        solder(lues);
      })
      .catch((exc: unknown) => {
        if (annule) return;
        setErreur(message(exc, "Lecture impossible"));
        solder(appsRef.current);
      });
    return () => {
      annule = true;
    };
  }, [tick, solder]);

  useEffect(() => {
    if (!fenetreVisible) return;
    const cadence = enAttente ? CADENCE_ATTENTE_MS : CADENCE_APPS_MS;
    const minuteur = setInterval(() => setTick((t) => t + 1), cadence);
    return () => clearInterval(minuteur);
  }, [fenetreVisible, enAttente]);

  const rafraichir = useCallback(() => setTick((t) => t + 1), []);

  /** Marque les opérations, exécute `action`, et lâche les marques si elle échoue. */
  const operer = useCallback(
    async (cles: string[], defaut: string, action: () => Promise<void>) => {
      setEchec(null);
      changerAttentes(ajouter(attentesRef.current, cles, Date.now()));
      try {
        await action();
      } catch (exc: unknown) {
        changerAttentes(retirer(attentesRef.current, cles));
        setErreur(message(exc, defaut));
        return;
      }
      rafraichir();
    },
    [rafraichir, changerAttentes],
  );

  const arreter = useCallback(
    (pid: number) =>
      operer([cleArret(pid)], "Arrêt impossible", async () => {
        await api.services.stopRunning(pid);
      }),
    [operer],
  );

  const arreterProjet = useCallback(
    (projectId: string, groupe: AppEnCours[]) =>
      operer(groupe.map((a) => cleArret(a.pid)), "Arrêt impossible", async () => {
        if (groupe.some((a) => a.origine === "tessera")) {
          await api.services.stop(projectId);
        }
        for (const externe of groupe.filter((a) => a.origine === "externe")) {
          await api.services.stopRunning(externe.pid);
        }
      }),
    [operer],
  );

  const lancer = useCallback(
    (projectId: string) =>
      operer([cleLancement(projectId)], "Lancement impossible", async () => {
        await api.services.start(projectId);
      }),
    [operer],
  );

  return {
    apps,
    lueA,
    erreur: erreur ?? echec,
    arreter,
    rafraichir,
    arreterProjet,
    lancer,
    enArret: (pid) => cleArret(pid) in attentes,
    enLancement: (projectId) => cleLancement(projectId) in attentes,
  };
}
