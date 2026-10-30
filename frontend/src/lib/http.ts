import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

/** Racine de l'API : les chemins que prennent `send` et `request` en partent. */
export const BASE = `${API_ORIGIN}/api/v1`;

async function messageDeLErreur(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return res.statusText;
  }
}

/**
 * The one door to the backend: adds the Bearer when a token is set and turns a
 * non-2xx answer into `API <code>: <text>`. `path` is relative to `/api/v1`.
 */
export async function send(path: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, authorized(options));
  if (!res.ok) throw new Error(`API ${res.status}: ${await messageDeLErreur(res)}`);
  return res;
}

/** Same as `send`, decoding the body as JSON. */
export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await send(path, options);
  return res.json() as Promise<T>;
}

/** Same as `send`, reading the body as text. */
export async function requestText(path: string, options?: RequestInit): Promise<string> {
  const res = await send(path, options);
  return res.text();
}
