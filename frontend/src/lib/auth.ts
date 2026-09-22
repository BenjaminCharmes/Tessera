/**
 * Authentification par token statique côté client (ticket-120).
 *
 * Quand le backend a `STATIC_TOKEN`, toute requête HTTP doit porter
 * `Authorization: Bearer <token>` et toute WebSocket `?token=<token>` — un
 * navigateur ne peut pas poser d'en-tête sur `new WebSocket(url)`. Le token se
 * lit à chaque appel plutôt qu'au chargement du module : le comportement avec
 * et sans token reste vérifiable dans le même processus de test.
 */

export function staticToken(): string {
  return import.meta.env.VITE_STATIC_TOKEN ?? "";
}

/** `init` enrichi du Bearer si un token est défini, `init` inchangé sinon. */
export function authorized(init?: RequestInit): RequestInit | undefined {
  const token = staticToken();
  if (!token) return init;
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

/** `url` avec `token=` ajouté à la query si un token est défini. */
export function withTokenQuery(url: string): string {
  const token = staticToken();
  if (!token) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(token)}`;
}
