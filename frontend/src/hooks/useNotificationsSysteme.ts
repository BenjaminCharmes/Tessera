import { useCallback, useEffect, useMemo, useRef } from "react";
import { isTauri } from "@tauri-apps/api/core";
import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";
import type { EntreeHistorique } from "../lib/historiqueNotifications";
import { notificationsRituels } from "../lib/notifRituels";
import type { Rituel } from "../lib/apiRituels";
import type { SidebarPanel } from "../components/Sidebar/panels";
import {
  masqueeParToast,
  notificationsPour,
  type Instantane,
  type Notif,
  type TypeNotif,
} from "../lib/notifications";
import {
  CLE_REGLAGES_PAR_TYPE,
  completerReglages,
  estReglagesParType,
  reglagesParDefaut,
  type ReglageDuType,
  type ReglagesMemorises,
  type ReglagesParType,
} from "../lib/reglagesNotifications";
import { enEtapeSilencieuse, santeAgent, type SanteAgent } from "../lib/santeAgent";
import { useEtatPersistant } from "./useEtatPersistant";
import { useHistoriqueNotifications } from "./useHistoriqueNotifications";
import { useMaintenant } from "./useMaintenant";
import { useQuotaLu } from "./useQuotaLu";
import type { UseSupervisionResult } from "./useSupervision";

/**
 * Une notification système quand un run a besoin de vous, ou finit — ticket-192.
 *
 * Dans l'app desktop, par le plugin Tauri (ticket-200) ; ailleurs, par l'API
 * `Notification` du web. La permission se demande au premier run lancé
 * (`demanderPermissionNotifications`), jamais au chargement.
 *
 * Le réglage est mémorisé par onglet (ticket-193). Une permission refusée
 * par le navigateur ne se redemande plus : `etat` le dit pour que l'écran
 * distingue « coupé » de « bloqué ».
 *
 * Pas de clic côté desktop (ticket-556), vérifié sur
 * `@tauri-apps/plugin-notification` 2.5.0 : `onAction` et
 * `onNotificationReceived` y sont documentés « only emitted on mobile », et
 * `onAction` exige en plus un type d'action posé par `registerActionTypes`,
 * lui aussi mobile. Aucune API 2.x ne donne donc le clic d'une notification
 * desktop : la fenêtre ne se ramène pas au premier plan, et la branche Tauri
 * de `envoyer` n'appelle pas `ouvrir`. À reprendre si une version ultérieure
 * ajoute un clic desktop.
 */
export type EtatDesNotifications = "actives" | "coupees" | "bloquees" | "indisponibles";

export const CLE_REGLAGE = "notifications";

function dansTauri(): boolean {
  try {
    return isTauri();
  } catch {
    return false;
  }
}

export function supportees(): boolean {
  return dansTauri() || (typeof window !== "undefined" && "Notification" in window);
}

export async function demanderPermissionNotifications(): Promise<void> {
  try {
    if (dansTauri()) {
      if (!(await isPermissionGranted())) await requestPermission();
      return;
    }
    if (!supportees() || Notification.permission !== "default") return;
    await Notification.requestPermission();
  } catch {
    // Un système qui refuse la demande n'empêche pas de lancer le run.
  }
}

export function etatDesNotifications(active: boolean): EtatDesNotifications {
  if (!supportees()) return "indisponibles";
  if (!active) return "coupees";
  if (!dansTauri() && Notification.permission === "denied") return "bloquees";
  return "actives";
}

async function envoyer(n: Notif, ouvrir: (n: Notif) => void): Promise<void> {
  if (dansTauri()) {
    if (!(await isPermissionGranted())) return;
    sendNotification({ title: n.titre, body: n.corps });
    return;
  }
  if (Notification.permission !== "granted") return;
  const notif = new Notification(n.titre, { body: n.corps, tag: n.titre });
  notif.onclick = () => {
    window.focus();
    ouvrir(n);
    notif.close();
  };
}

/** Ce que la cloche affiche et règle : l'historique du jour et les cases par type. */
export interface DonneesDeLaCloche {
  historique: EntreeHistorique[];
  nonLus: number;
  toutMarquerLu: () => void;
  reglages: ReglagesParType;
  setReglage: (type: TypeNotif, champ: keyof ReglageDuType, valeur: boolean) => void;
  ouvrir: (projectId: string) => void;
  /** Ouvre un panneau du rail : la cible d'une entrée de type `rituel`. */
  ouvrirPanneau?: (panneau: SidebarPanel) => void;
}

export function useNotificationsSysteme(
  supervision: Pick<UseSupervisionResult, "runs" | "etatDe">,
  projetActif: string | null,
  ouvrir: (projectId: string) => void,
  rituels: Rituel[] = [],
  ouvrirPanneau?: (panneau: SidebarPanel) => void,
): {
  active: boolean;
  setActive: (v: boolean) => void;
  etat: EtatDesNotifications;
  cloche: DonneesDeLaCloche;
} {
  const [active, setActive] = useEtatPersistant<boolean>(
    CLE_REGLAGE,
    true,
    (v): v is boolean => typeof v === "boolean",
  );
  const [memorises, setReglages] = useEtatPersistant<ReglagesMemorises>(
    CLE_REGLAGES_PAR_TYPE,
    reglagesParDefaut(),
    estReglagesParType,
  );
  // Un réglage mémorisé avant un type reçoit le défaut de ce type (ticket-840).
  const reglages = useMemo(() => completerReglages(memorises), [memorises]);
  const { historique, nonLus, enregistrer, toutMarquerLu } = useHistoriqueNotifications();
  const setReglage = useCallback(
    (type: TypeNotif, champ: keyof ReglageDuType, valeur: boolean) =>
      setReglages((prev) => {
        const complets = completerReglages(prev);
        return { ...complets, [type]: { ...complets[type], [champ]: valeur } };
      }),
    [setReglages],
  );
  const precedent = useRef<Instantane>({ runs: [], etats: {} });
  const { runs, etatDe } = supervision;
  // La santé dépend du temps : sans tick, un agent muet ne changerait jamais d'état.
  const maintenant = useMaintenant();
  const quota = useQuotaLu(maintenant);
  const rituelsAvant = useRef<Rituel[]>([]);

  // Une notification de rituel ouvre la vue Rituels, les autres leur projet.
  const ouvrirNotif = useCallback(
    (n: Notif) => (n.type === "rituel" ? ouvrirPanneau?.("rituels") : ouvrir(n.projectId)),
    [ouvrir, ouvrirPanneau],
  );

  useEffect(() => {
    const avant = rituelsAvant.current;
    rituelsAvant.current = rituels;
    const notifs = notificationsRituels(avant, rituels);
    if (notifs.length === 0) return;
    enregistrer(notifs);
    if (!active || !supportees() || !reglages.rituel.systeme) return;
    for (const n of notifs) void envoyer(n, ouvrirNotif).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- seule une nouvelle lecture des rituels notifie
  }, [rituels]);

  useEffect(() => {
    const etats: Record<string, ReturnType<typeof etatDe>> = {};
    const sante: Record<string, SanteAgent> = {};
    for (const r of runs) {
      const etat = etatDe(r.run_id);
      etats[r.run_id] = etat;
      if (etat.status === "running") {
        sante[r.run_id] = santeAgent(
          etat.dernierEvenementA,
          maintenant,
          etat.pendingQuestion,
          etat.attenteExterieure !== null,
          enEtapeSilencieuse(etat),
        );
      }
    }
    const courant: Instantane = { runs, etats, sante, quota, maintenant };
    const avant = precedent.current;
    precedent.current = courant;

    // L'historique prend tout, avant les filtres de l'envoi (ticket-554).
    const notifs = notificationsPour(avant, courant);
    if (notifs.length > 0) enregistrer(notifs);

    if (!active || !supportees()) return;
    const vue = { projetActif, visible: document.visibilityState === "visible" };
    for (const n of notifs) {
      if (!reglages[n.type].systeme || masqueeParToast(n, vue)) continue;
      // Une notification qui ne part pas ne casse rien.
      void envoyer(n, ouvrirNotif).catch(() => undefined);
    }
  }, [runs, etatDe, maintenant, quota, active, projetActif, ouvrirNotif, reglages, enregistrer]);

  return {
    active,
    setActive,
    etat: etatDesNotifications(active),
    cloche: { historique, nonLus, toutMarquerLu, reglages, setReglage, ouvrir, ouvrirPanneau },
  };
}
