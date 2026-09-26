import { useEffect, useRef } from "react";
import { isTauri } from "@tauri-apps/api/core";
import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";
import { notificationsPour, type Instantane, type Notif } from "../lib/notifications";
import { useEtatPersistant } from "./useEtatPersistant";
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
 * distingue « coupé » de « bloqué ». Le plugin, lui, n'a pas de clic : la
 * fenêtre ne se ramène pas au premier plan depuis une notification desktop.
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

async function envoyer(n: Notif, ouvrir: (projectId: string) => void): Promise<void> {
  if (dansTauri()) {
    if (!(await isPermissionGranted())) return;
    sendNotification({ title: n.titre, body: n.corps });
    return;
  }
  if (Notification.permission !== "granted") return;
  const notif = new Notification(n.titre, { body: n.corps, tag: n.titre });
  notif.onclick = () => {
    window.focus();
    ouvrir(n.projectId);
    notif.close();
  };
}

export function useNotificationsSysteme(
  supervision: Pick<UseSupervisionResult, "runs" | "etatDe">,
  projetActif: string | null,
  ouvrir: (projectId: string) => void,
): { active: boolean; setActive: (v: boolean) => void; etat: EtatDesNotifications } {
  const [active, setActive] = useEtatPersistant<boolean>(
    CLE_REGLAGE,
    true,
    (v): v is boolean => typeof v === "boolean",
  );
  const precedent = useRef<Instantane>({ runs: [], etats: {} });
  const { runs, etatDe } = supervision;

  useEffect(() => {
    const etats: Record<string, ReturnType<typeof etatDe>> = {};
    for (const r of runs) etats[r.run_id] = etatDe(r.run_id);
    const courant: Instantane = { runs, etats };
    const avant = precedent.current;
    precedent.current = courant;

    if (!active || !supportees()) return;
    const vue = { projetActif, visible: document.visibilityState === "visible" };
    for (const n of notificationsPour(avant, courant, vue)) {
      // Une notification qui ne part pas ne casse rien.
      void envoyer(n, ouvrir).catch(() => undefined);
    }
  }, [runs, etatDe, active, projetActif, ouvrir]);

  return { active, setActive, etat: etatDesNotifications(active) };
}
