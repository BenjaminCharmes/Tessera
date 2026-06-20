// Dual-mode file access: Tauri invoke when running as desktop app, REST API fallback for web
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
  const res = await fetch(`/api/v1/fs/read?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`Failed to read ${path}: ${res.statusText}`);
  return res.text();
}

export async function writeFile(path: string, content: string): Promise<void> {
  if (isTauri) {
    return tauriInvoke<void>("write_file", { path, content });
  }
  const res = await fetch("/api/v1/fs/write", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) throw new Error(`Failed to write ${path}: ${res.statusText}`);
}

export async function listDir(path: string): Promise<string[]> {
  if (isTauri) {
    return tauriInvoke<string[]>("list_dir", { path });
  }
  const res = await fetch(`/api/v1/fs/list?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`Failed to list ${path}: ${res.statusText}`);
  return res.json() as Promise<string[]>;
}
