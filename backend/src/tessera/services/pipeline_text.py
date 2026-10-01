"""Pure text helpers used by the pipeline: commit messages and agent-output parsing.

Split out of `orchestrator.py` so they can be read and tested on their own —
none of them touch git, the ticket store or the agents.
"""
import re

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
        if _CRITERIA_HEADING.search(line):
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
    for line in lines:
        verdict = _verdict_line(line)
        if verdict is not None:
            return verdict
    for line in lines:
        if "CHANGES_REQUESTED" in line.upper():
            reason = line.split(":", 1)[-1].strip() if ":" in line else ""
            return False, reason
    if any(_APPROVED_WORD.search(line) for line in lines):
        return True, ""
    return False, content[:200]
