import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

// Le backend est la seule porte vers le disque : `routers/fs.py` refuse tout
// chemin hors workspace. Le shell desktop n'a plus de commande fichier à lui
// (ticket-124) — il n'offre donc pas plus d'accès que l'API.
const BASE = `${API_ORIGIN}/api/v1/fs`;

export async function readFile(path: string): Promise<string> {
  const res = await fetch(`${BASE}/read?path=${encodeURIComponent(path)}`, authorized());
  if (!res.ok) throw new Error(`Failed to read ${path}: ${res.statusText}`);
  return res.text();
}

export async function writeFile(path: string, content: string): Promise<void> {
  const res = await fetch(
    `${BASE}/write`,
    authorized({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }),
  );
  if (!res.ok) throw new Error(`Failed to write ${path}: ${res.statusText}`);
}

export async function listDir(path: string): Promise<string[]> {
  const res = await fetch(`${BASE}/list?path=${encodeURIComponent(path)}`, authorized());
  if (!res.ok) throw new Error(`Failed to list ${path}: ${res.statusText}`);
  return res.json() as Promise<string[]>;
}

/** Une entrée de dossier telle que la renvoie `GET /api/v1/fs/list`. */
export interface DirEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

/** Liste un dossier, avec le type de chaque entrée (ticket-065). */
export async function listEntries(path: string): Promise<DirEntry[]> {
  const res = await fetch(`${BASE}/list?path=${encodeURIComponent(path)}`, authorized());
  if (!res.ok) throw new Error(`Failed to list ${path}: ${res.statusText}`);
  return res.json() as Promise<DirEntry[]>;
}
