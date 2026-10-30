/** Ce que `GET /api/v1/tessera/salle` rend — ticket-726. */
export interface ProcessusDeTessera {
  nom: string;
  port: number;
  pid: number | null;
  memoire_mo: number;
  demarre_a: string | null;
}

export interface RunVivant {
  project_id: string;
  ticket_id: string | null;
  agent: string | null;
  etape: string | null;
  file_index: number;
  file_total: number;
  suivants: string[];
}

export interface LigneDeJournal {
  ts: string | null;
  niveau: string;
  evenement: string;
  ticket_id: string | null;
  role: string | null;
}

export interface SalleTessera {
  processus: ProcessusDeTessera[];
  ollama: { url: string; refroidissement_s: number | null };
  runs: RunVivant[];
  ci_en_attente: Record<string, string[]>;
  journal: LigneDeJournal[];
  base_mo: number;
  worktrees: number;
}
