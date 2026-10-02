/**
 * Parses the reviewer's response to determine whether it is approved or not.
 *
 * Mirrors `services/pipeline_text._parse_reviewer_verdict` (ADR-009, ticket-298).
 * The first line that *starts with* a verdict keyword wins; the fallback
 * (CHANGES_REQUESTED anywhere, then APPROVED as a whole word) is used when no
 * such line exists.
 */

// Markdown decoration stripped before checking the start of a line.
const DECORATION = /^[ \t*_`#>]+/;

// Whole-word APPROVED match used in the fallback.
const APPROVED_WORD = /\bAPPROVED\b/;

/**
 * Returns the verdict carried by a single line, or null when the line does not
 * open with a verdict keyword.
 */
function verdictLine(line: string): "APPROVED" | "CHANGES_REQUESTED" | null {
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
 * Extracts the reviewer verdict from its full response text.
 *
 * Returns "APPROVED" or "CHANGES_REQUESTED". A response with no recognisable
 * verdict is treated as "CHANGES_REQUESTED".
 */
export function verdictDuReviewer(
  content: string,
): "APPROVED" | "CHANGES_REQUESTED" {
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
