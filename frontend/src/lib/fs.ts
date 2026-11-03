import { request, requestText, send } from "./http";

// Le backend est la seule porte vers le disque : `routers/fs.py` refuse tout
// chemin hors workspace. Le shell desktop n'a plus de commande fichier à lui
// (ticket-124) — il n'offre donc pas plus d'accès que l'API.
const FS = "/fs";

/** Rethrow a failed call as `Failed to <action> <path>: <cause>`. */
async function echouerAvecLeChemin<T>(action: string, path: string, appel: () => Promise<T>): Promise<T> {
  try {
    return await appel();
  } catch (erreur) {
    const cause = erreur instanceof Error ? erreur.message : String(erreur);
    throw new Error(`Failed to ${action} ${path}: ${cause}`, { cause: erreur });
  }
}

export function readFile(path: string): Promise<string> {
  return echouerAvecLeChemin("read", path, () => requestText(`${FS}/read?path=${encodeURIComponent(path)}`));
}

export async function writeFile(path: string, content: string): Promise<void> {
  await echouerAvecLeChemin("write", path, () =>
    send(`${FS}/write`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }),
  );
}

export function listDir(path: string): Promise<string[]> {
  return echouerAvecLeChemin("list", path, () => request<string[]>(`${FS}/list?path=${encodeURIComponent(path)}`));
}

/** Une entrée de dossier telle que la renvoie `GET /api/v1/fs/list`. */
export interface DirEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

/** Liste un dossier, avec le type de chaque entrée (ticket-065). */
export function listEntries(path: string): Promise<DirEntry[]> {
  return echouerAvecLeChemin("list", path, () => request<DirEntry[]>(`${FS}/list?path=${encodeURIComponent(path)}`));
}
