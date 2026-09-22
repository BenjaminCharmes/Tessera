// Dual-mode file access: Tauri invoke when running as desktop app, REST API fallback for web
import { authorized } from "./auth";

const isTauri =
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

async function tauriInvoke<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

export async function readFile(path: string): Promise<string> {
  if (isTauri) {
    return tauriInvoke<string>("read_file", { path });
  }
  const res = await fetch(
    `/api/v1/fs/read?path=${encodeURIComponent(path)}`,
    authorized(),
  );
  if (!res.ok) throw new Error(`Failed to read ${path}: ${res.statusText}`);
  return res.text();
}

export async function writeFile(path: string, content: string): Promise<void> {
  if (isTauri) {
    return tauriInvoke<void>("write_file", { path, content });
  }
  const res = await fetch(
    "/api/v1/fs/write",
    authorized({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }),
  );
  if (!res.ok) throw new Error(`Failed to write ${path}: ${res.statusText}`);
}

export async function listDir(path: string): Promise<string[]> {
  if (isTauri) {
    return tauriInvoke<string[]>("list_dir", { path });
  }
  const res = await fetch(
    `/api/v1/fs/list?path=${encodeURIComponent(path)}`,
    authorized(),
  );
  if (!res.ok) throw new Error(`Failed to list ${path}: ${res.statusText}`);
  return res.json() as Promise<string[]>;
}

/** Une entrée de dossier telle que la renvoie `GET /api/v1/fs/list`. */
export interface DirEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

/**
 * Liste un dossier, avec le type de chaque entrée (ticket-065).
 *
 * Passe toujours par le backend, **y compris sous Tauri** : la commande Rust
 * `list_dir` ne renvoie que des noms, sans dire lesquels sont des dossiers, et
 * un arbre a besoin de le savoir. Le backend tourne de toute façon — tout le
 * reste de l'application l'interroge déjà en HTTP — donc s'en remettre à lui
 * ici évite de faire diverger deux implémentations pour un seul appel.
 */
export async function listEntries(path: string): Promise<DirEntry[]> {
  const res = await fetch(
    `/api/v1/fs/list?path=${encodeURIComponent(path)}`,
    authorized(),
  );
  if (!res.ok) throw new Error(`Failed to list ${path}: ${res.statusText}`);
  return res.json() as Promise<DirEntry[]>;
}
