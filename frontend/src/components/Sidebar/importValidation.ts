export type SourceType = "local" | "github";
export type ImportMode = "symlink" | "copy";

const GITHUB_URL = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;

/** Return the error message for a local folder path, or null when valid. */
export function validateLocalPath(value: string): string | null {
  if (!value.trim()) return "Le chemin est requis";
  return null;
}

/** Return the error message for a GitHub repository URL, or null when valid. */
export function validateGithubUrl(value: string): string | null {
  if (!value.trim()) return "L'URL est requise";
  if (!GITHUB_URL.test(value.trim())) {
    return "Format invalide — ex : https://github.com/owner/mon-repo";
  }
  return null;
}
