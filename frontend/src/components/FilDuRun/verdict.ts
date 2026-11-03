/**
 * Le verdict du reviewer, lu à un seul endroit.
 *
 * La source est le champ `verdict` de `agent_done` (ticket-614). Seul un
 * événement qui n'en porte pas — un run enregistré avant ce ticket, relu dans
 * l'historique — retombe sur la lecture par mot-clé, isolée dans
 * `verdictParMotCle`.
 */
import type { OrchestratorEvent } from "../../types/api";

/**
 * Le verdict du reviewer, porté par le champ `verdict` de `agent_done`
 * (ticket-614). Absent des runs enregistrés avant ce ticket.
 */
export type VerdictReviewer = "APPROVED" | "CHANGES_REQUESTED";

/** Ce qu'il faut d'un passage du reviewer pour en lire le verdict. */
export interface EntreeDeRevue {
  content: string;
  verdict?: VerdictReviewer;
}

/** Le champ `verdict` d'un `data` d'événement, ou undefined s'il est absent ou hors vocabulaire. */
export function verdictDeData(data: Record<string, unknown>): VerdictReviewer | undefined {
  const v = data["verdict"];
  return v === "APPROVED" || v === "CHANGES_REQUESTED" ? v : undefined;
}

/** Le passage du reviewer porté par un événement `agent_done`. */
export function revueDeLEvenement(ev: OrchestratorEvent): EntreeDeRevue {
  const contenu = ev.data["content"];
  return { content: typeof contenu === "string" ? contenu : "", verdict: verdictDeData(ev.data) };
}

/**
 * Le verdict du reviewer : `verdict` quand il est présent, quel que soit le
 * texte ; sinon la lecture par mot-clé du texte (événement d'avant le
 * ticket-614). Une chaîne seule vaut un passage sans `verdict`.
 */
export function verdictDuReviewer(entry: string | EntreeDeRevue): VerdictReviewer {
  if (typeof entry === "string") return verdictParMotCle(entry);
  return entry.verdict ?? verdictParMotCle(entry.content);
}

// ---------------------------------------------------------------------------
// Lecture par mot-clé — la seule trace du parseur côté interface
// ---------------------------------------------------------------------------

// Markdown decoration stripped before checking the start of a line.
const DECORATION = /^[ \t*_`#>]+/;

// Whole-word APPROVED match used in the fallback.
const APPROVED_WORD = /\bAPPROVED\b/;

/**
 * Returns the verdict carried by a single line, or null when the line does not
 * open with a verdict keyword.
 */
function verdictLine(line: string): VerdictReviewer | null {
  const stripped = line.replace(DECORATION, "");
  if (stripped.toUpperCase().startsWith("CHANGES_REQUESTED")) {
    return "CHANGES_REQUESTED";
  }
  if (stripped.startsWith("APPROVED")) {
    // « APPROVED serait prématuré : CHANGES_REQUESTED » stays a refusal.
    if (stripped.toUpperCase().includes("CHANGES_REQUESTED")) {
      return "CHANGES_REQUESTED";
    }
    return "APPROVED";
  }
  return null;
}

/**
 * Extracts the reviewer verdict from the text of its response, for events that
 * carry no `verdict` field.
 *
 * Mirrors `services/pipeline_text._parse_reviewer_verdict` (ADR-009, ticket-298):
 * the first line that *starts with* a verdict keyword wins; the fallback
 * (CHANGES_REQUESTED anywhere, then APPROVED as a whole word) is used when no
 * such line exists. A response with no recognisable verdict is refused.
 */
function verdictParMotCle(content: string): VerdictReviewer {
  const lines = content.split("\n");

  // Pass 1: first line that starts with a verdict keyword.
  for (const line of lines) {
    const v = verdictLine(line);
    if (v !== null) {
      return v;
    }
  }

  // Pass 2 fallback: CHANGES_REQUESTED anywhere.
  for (const line of lines) {
    if (line.toUpperCase().includes("CHANGES_REQUESTED")) {
      return "CHANGES_REQUESTED";
    }
  }

  // Pass 3 fallback: whole-word APPROVED.
  if (lines.some((l) => APPROVED_WORD.test(l))) {
    return "APPROVED";
  }

  return "CHANGES_REQUESTED";
}

/**
 * Le texte de la revue sans les lignes qui nomment un verdict : le bandeau
 * affiche le verdict lui-même, il ne reste à montrer que le propos.
 */
export function revueSansLigneDeVerdict(content: string): string[] {
  return content
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.includes("APPROVED") && !l.includes("CHANGES_REQUESTED"));
}
