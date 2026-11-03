export interface Project {
  id: string;
  name: string;
  /** Chemin absolu du projet sur le disque — sert à l'ouvrir dans VSCode. */
  path: string;
  description: string;
  active_agents: string[];
  stack: string | null;
  raw_claude_md: string;
  github_remote: string | null;
  /** Le rangement déclaré dans agents.json — null si le projet n'en déclare pas (ticket-175). */
  category?: string | null;
  /**
   * Ce projet execute l'IDE en ce moment (ticket-152). Lui proposer
   * « Lancer » demarrerait un second backend sur un port deja pris.
   */
  fait_tourner_l_ide?: boolean;
}

export interface ProjectCreationResult {
  project: Project;
  agents_created: string[];
  /**
   * Le projet est-il la racine d'un dépôt git utilisable (ticket-104) ?
   * Faux si l'initialisation a échoué : le projet existe alors sur disque,
   * mais aucun run n'y démarrera tant qu'on n'aura pas rattrapé à la main.
   */
  repository_ready: boolean;
}

/** Résultat de la création depuis le gabarit FastAPI + React (ticket-373). */
export interface TemplateCreationResult {
  project: Project;
  backend_port: number;
  frontend_port: number;
  git_ready: boolean;
}

export interface ImportProjectRequest {
  source_path: string;
  mode: "copy" | "symlink";
  project_id?: string;
}

export interface ImportProjectResponse {
  project: Project;
}

export interface AnalysisResult {
  claude_md: string;
  detected_stack: string[];
  suggested_agents: string[];
  claude_md_written: boolean;
}

export interface CloneProjectRequest {
  repo_url: string;
  project_id?: string;
}

export interface CloneProjectResponse {
  project: Project;
  claude_md_generated: boolean;
  detected_stack: string[];
}

/** Une app de projet qui tourne sur la machine (ticket-416). */
export interface AppEnCours {
  project_id: string;
  project_name: string;
  nom: string;
  /** `tessera` : lancée par le registre ; `externe` : lancée à la main. */
  origine: "tessera" | "externe";
  pid: number;
  ports: number[];
  /** ISO 8601, `null` quand la sonde ne connaît pas l'heure de démarrage. */
  demarre_a: string | null;
  memoire_mo: number;
}

/** Un service lance pour un projet (ticket-137). */
export interface ServiceActif {
  nom: string;
  project_id: string;
  /** `null` pour un service declare mais pas lance (ticket-146). */
  pid: number | null;
  demarre_a: string;
  en_cours: boolean;
  code_de_sortie: number | null;
  /**
   * Les dernieres lignes que le service a ecrites, gardees par le backend
   * (ticket-148). Le canal ne rejoue pas l'historique : sans elles, qui ouvre
   * l'IDE apres le demarrage ne verrait jamais l'adresse annoncee.
   */
  sortie?: string[];
  /**
   * Vrai quand c'est l'utilisateur qui a demande l'arret (ticket-151).
   * `terminate()` laisse un code non nul sur certaines plateformes : sans ce
   * drapeau, un service qu'on vient d'arreter s'afficherait en echec.
   */
  arrete_a_la_main?: boolean;
}

// ---------------------------------------------------------- liaison git ----
// ticket-061 — un projet créé de zéro ou importé en `copy` n'a aucun dépôt.

export interface GitStatus {
  is_repository: boolean;
  has_commits: boolean;
  remote_url: string | null;
  /** Renseigné quand le projet vit dans un dépôt qui n'est pas le sien. */
  nested_in: string | null;
  /** Le projet déclare `git_root: ancestor` et travaille dans le dépôt qui le
   *  contient — ce n'est pas une anomalie à corriger (ticket-171). */
  uses_parent_repository: boolean;
}

/** ticket-062 — les artefacts Tessera partent dans le dépôt, ou restent locaux. */
export type ArtifactMode = "tracked" | "local";

export interface ArtifactModeState {
  mode: ArtifactMode;
  /** Artefacts déjà dans l'index git : l'exclusion ne les en sort pas. */
  already_tracked: string[];
}

/** ticket-063 — ce qu'un retrait toucherait, à montrer avant de décider. */
export interface RemovalPlan {
  project_id: string;
  /** Chemin réellement visé, liens résolus. */
  real_path: string;
  is_symlink: boolean;
  unpushed_commits: number;
}

export type StripeMode = "test" | "live";

/** Ce qu'une étape de mise en ligne a trouvé ou fait (ADR-053). */
export type EtatEtape =
  | "todo"
  | "done"
  | "skipped"
  | "pending"
  | "manual"
  | "needs_human"
  | "failed";

/** Une étape et son état ; `detail` ne porte jamais de secret. */
export interface EtapeMiseEnLigne {
  step: string;
  state: EtatEtape;
  detail: string;
}
