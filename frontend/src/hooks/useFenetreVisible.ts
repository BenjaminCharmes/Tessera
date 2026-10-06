import { useEffect, useState } from "react";

/**
 * Renvoie `true` quand la fenêtre est visible, `false` quand elle est cachée.
 *
 * Basé sur `document.visibilityState` et l'événement `visibilitychange`
 * (ticket-356). Utilisé pour suspendre le polling quand personne ne regarde :
 * `useTickets`, `useServices` et le polling PR de `TicketCard` s'y abonnent.
 */
export function useFenetreVisible(): boolean {
  const [visible, setVisible] = useState<boolean>(
    () =>
      typeof document === "undefined" ||
      document.visibilityState !== "hidden",
  );

  useEffect(() => {
    const handler = () =>
      setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  return visible;
}
