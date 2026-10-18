"""Pure text helpers used by the pipeline: commit messages and agent-output parsing.

Split out of `orchestrator.py` so they can be read and tested on their own —
none of them touch git, the ticket store or the agents.
"""
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tessera.services.pipeline_run import PipelineRun

_CRITERIA_HEADING = re.compile(r"##\s*(critères|acceptance criteria)", re.IGNORECASE)
_CRITERIA_ITEM = re.compile(r"\s*-\s*\[[ xX]?\]\s*(.+)")


def _single_line(text: str) -> str:
    """Collapse any run of whitespace (newlines included) into single spaces.

    Agent-produced text is interpolated into a commit *subject*: a newline
    there silently splits the message into subject + body, leaving a
    truncated and misleading one-liner in `git log --oneline`.
    """
    return " ".join(text.split())


# Non-approved work is still committed — on its own ticket branch, under a
# `chore:` message rather than the ticket-typed one reserved for approved
# work — so the user can inspect it via `git show`/`git diff` on that
# branch, and so the tree is clean again for the next ticket in an
# autonomous run. `chore` and not `wip`: this message lands in the *user's*
# repository, which follows Conventional Commits, and `wip` is not one of
# its types. The reason names why the run did not pass: "changes requested"
# (rounds exhausted without an APPROVED verdict) or "security block".
def _unapproved_commit_message(ticket_id: str, reason: str) -> str:
    return f"chore: {ticket_id} — unapproved work ({_single_line(reason)})"


_CONTINUATION_LINE = re.compile(r"^[ \t]+\S")


def _extract_criteria(ticket_body: str) -> list[str]:
    """Extracts acceptance criteria checkboxes from ticket markdown body.

    A criterion may span several lines: indented lines immediately following
    a checkbox line are treated as continuations and joined with a space.
    A blank line or a new checkbox terminates the current criterion.
    """
    criteria: list[str] = []
    in_criteria_section = False
    # Vrai tant que la ligne précédente appartient au critère en cours : une
    # ligne vide le clôt, sinon un paragraphe indenté plus bas s'y collerait.
    continuable = False
    for line in ticket_body.splitlines():
        if _CRITERIA_HEADING.match(line):
            in_criteria_section = True
            continue
        if not in_criteria_section:
            continue
        if line.startswith("##"):
            break
        m = _CRITERIA_ITEM.match(line)
        if m:
            criteria.append(m.group(1).strip())
            continuable = True
        elif continuable and _CONTINUATION_LINE.match(line):
            # Indented non-empty line right after a criterion: continuation.
            criteria[-1] = criteria[-1] + " " + line.strip()
        else:
            continuable = False
    return criteria


OBJECTION_MAX_CHARS = 4000
_TRUNCATION_MARK = "\n[…] tronqué"


def _truncate_objection(text: str) -> str:
    """Cap an objection at `OBJECTION_MAX_CHARS`, flagging the cut."""
    if len(text) <= OBJECTION_MAX_CHARS:
        return text
    return text[:OBJECTION_MAX_CHARS] + _TRUNCATION_MARK


def _first_line(text: str) -> str:
    """The first non-blank line of `text`, stripped; empty when there is none."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _compose_feedback(
    rev_approved: bool,
    rev_reason: str,
    raw_verdict: str,
    val_approved: bool,
    val_reason: str,
) -> str:
    """The feedback handed back to the coder after a refused round.

    Names the author when both refuse: the coder sees a single feedback at the
    next round and must know who objects to what.
    """
    parts: list[str] = []
    if not rev_approved:
        parts.append(f"Reviewer : {_truncate_objection(rev_reason or raw_verdict)}")
    if not val_approved:
        parts.append(f"Validateur : {val_reason}")
    return "\n\n".join(parts) if parts else _truncate_objection(raw_verdict)


_APPROVED_WORD = re.compile(r"\bAPPROVED\b")
_APPROVED_LEADING = re.compile(r"APPROVED\b")
# Ce qui entoure un verdict sans en changer le sens : `**APPROVED**`,
# `## CHANGES_REQUESTED`, `` `APPROVED` ``.
_DECORATION = " \t*_`#>"


def _verdict_line(line: str) -> tuple[bool, str] | None:
    """The verdict a line opens with, or None when it opens with something else."""
    s = line.strip().strip(_DECORATION)
    if s.upper().startswith("CHANGES_REQUESTED"):
        reason = s.split(":", 1)[-1].strip() if ":" in s else ""
        return False, reason
    if _APPROVED_LEADING.match(s):
        # « APPROVED serait prématuré : CHANGES_REQUESTED » reste un refus.
        if "CHANGES_REQUESTED" in s.upper():
            return False, s
        return True, ""
    return None


def _parse_reviewer_verdict(content: str) -> tuple[bool, str]:
    """Returns (approved, reason) from the reviewer's answer.

    Le reviewer est prompté pour ouvrir sa réponse par le verdict, seul sur sa
    ligne (ADR-009). La première ligne qui *commence* par un verdict le
    porte : un reviewer qui cite `CHANGES_REQUESTED` dans le corps d'une
    approbation n'est plus lu comme un refus (ticket-298, trois APPROVED
    refusés sur le ticket-288).

    Sans ligne de verdict, la règle d'avant tient : `CHANGES_REQUESTED`
    n'importe où l'emporte, puis `APPROVED` en mot entier et en majuscules —
    « this should not be approved » n'approuve rien (ticket-122).
    """
    lines = content.splitlines()
    for index, line in enumerate(lines):
        verdict = _verdict_line(line)
        if verdict is None:
            continue
        approved, reason = verdict
        # Le verdict seul sur sa ligne ne porte aucune raison : elle est dans
        # le texte qui suit, et c'est ce que le codeur doit lire (ticket-474).
        if not approved and not reason:
            reason = "\n".join(lines[index + 1:]).strip()
        return approved, reason
    for line in lines:
        if "CHANGES_REQUESTED" in line.upper():
            reason = line.split(":", 1)[-1].strip() if ":" in line else ""
            return False, reason
    if any(_APPROVED_WORD.search(line) for line in lines):
        return True, ""
    return False, content[:200]


def _echec_de_tests(run: "PipelineRun") -> str:
    """Ce que le codeur lit au tour suivant : le fait, puis les erreurs.

    Sans les erreurs, le second tour recommence à l'aveugle et produit
    souvent la même chose.
    """
    resultat = run.test_result
    if resultat is None:
        return "Les tests du projet ont échoué. Corrige-les avant toute chose."
    erreurs = "\n".join(resultat.errors[:10])
    return (
        "Les tests du projet échouent — corrige-les avant toute autre chose.\n"
        f"{resultat.output_summary}\n{erreurs}"
    )
