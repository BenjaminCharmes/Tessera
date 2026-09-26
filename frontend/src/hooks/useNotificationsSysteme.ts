import { useEffect, useRef } from "react";
import { notificationsPour, type Instantane } from "../lib/notifications";
import { useEtatPersistant } from "./useEtatPersistant";
import type { UseSupervisionResult } from "./useSupervision";

/**
 * Une notification système quand un run a besoin de vous, ou finit — ticket-192.
 *
 * Par l'API `Notification` du web : elle sert dans le navigateur, et dans la
 * WebView quand elle la porte. La permission se demande au premier run
 * lancé (`demanderPermissionNotifications`), jamais au chargement.
 *
 * Le réglage est mémorisé par onglet (ticket-193). Une permission refusée
 * par le navigateur ne se redemande plus : `etat` le dit pour que l'écran
 * distingue « coupé » de « bloqué ».
 */
export type EtatDesNotifications = "actives" | "coupees" | "bloquees" | "indisponibles";

export const CLE_REGLAGE = "notifications";

export function supportees(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export async function demanderPermissionNotifications(): Promise<void> {
  if (!supportees() || Notification.permission !== "default") return;
  try {
    await Notification.requestPermission();
  } catch {
    // Un navigateur qui refuse la demande n'empêche pas de lancer le run.
  }
}

export function etatDesNotifications(active: boolean): EtatDesNotifications {
  if (!supportees()) return "indisponibles";
  if (!active) return "coupees";
  if (Notification.permission === "denied") return "bloquees";
  return "actives";
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

    if (!active || !supportees() || Notification.permission !== "granted") return;
    const vue = { projetActif, visible: document.visibilityState === "visible" };
    for (const n of notificationsPour(avant, courant, vue)) {
      try {
        const notif = new Notification(n.titre, { body: n.corps, tag: n.titre });
        notif.onclick = () => {
          window.focus();
          ouvrir(n.projectId);
          notif.close();
        };
      } catch {
        // Une notification qui ne part pas ne casse rien.
      }
    }
  }, [runs, etatDe, active, projetActif, ouvrir]);

  return { active, setActive, etat: etatDesNotifications(active) };
}
