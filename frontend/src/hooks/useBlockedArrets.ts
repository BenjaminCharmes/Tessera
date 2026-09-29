import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

/**
 * The stop reason of the last blocked run, indexed by ticket id — ticket-218.
 *
 * Only blocked tickets are fetched; the list is usually empty or very short.
 * A failed fetch silently returns null for that ticket so a transient error
 * never hides the card.
 */
export function useBlockedArrets(
  projectId: string | null,
  blockedIds: string[],
): Record<string, string | null> {
  // Rangés sous la clé de la requête qui les a produits : une liste vide ou
  // un autre projet rendent `{}` sans setState dans l'effet.
  const [lu, setLu] = useState<{ cle: string; arrets: Record<string, string | null> }>({
    cle: "",
    arrets: {},
  });

  // Sort + join to keep a stable dependency value without including the array
  // reference itself (changes identity on every render).
  const key = useMemo(() => [...blockedIds].sort().join(","), [blockedIds]);

  useEffect(() => {
    if (!projectId || blockedIds.length === 0) return;
    let cancelled = false;
    void Promise.all(
      blockedIds.map((id) =>
        api.tickets
          .activity(projectId, id)
          .then((a) => {
            const run = a.runs
              .filter((r) => r.final_status === "blocked")
              .at(-1);
            return [id, run?.arret ?? null] as [string, string | null];
          })
          .catch(() => [id, null] as [string, string | null]),
      ),
    ).then((pairs) => {
      if (cancelled) return;
      setLu({ cle: `${projectId}|${key}`, arrets: Object.fromEntries(pairs) });
    });
    return () => {
      cancelled = true;
    };
    // `blockedIds` is captured through `key` which is stable; eslint does not
    // know that, so silence it here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, key]);

  return lu.cle === `${projectId}|${key}` ? lu.arrets : {};
}
