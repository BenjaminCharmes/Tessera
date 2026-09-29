"""CI check of a pull request against FORBIDDEN_TERMS (ADR-048) — ticket-230.

Checks what the pull request would publish: lines added between the base and
the head, full commit messages, authors and committers, and the PR title and
body. Matching reuses the pre-push hook's functions, so the CI and the hook
cannot disagree on what a forbidden term is (ADR-034).

Names locations, never terms: a CI log is public on a public repository.
A missing list refuses the PR — a check that could not run approved nothing.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parent / "hooks" / "pre-push"


def charger_hook() -> types.ModuleType:
    """Load scripts/hooks/pre-push as a module (it has no .py suffix)."""
    loader = importlib.machinery.SourceFileLoader("pre_push_hook", str(HOOK_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def main() -> int:
    """Entry point of the CI job; returns the process exit code."""
    brut = os.environ.get("FORBIDDEN_TERMS", "")
    if not brut.strip():
        print("FORBIDDEN_TERMS absent : contrôle impossible, PR refusée.", file=sys.stderr)
        return 1
    hook = charger_hook()
    patterns = hook._build_patterns(
        [hook._normaliser(t.strip()) for t in brut.split(",") if t.strip()]
    )
    base, head = os.environ["BASE_SHA"], os.environ["HEAD_SHA"]
    try:
        commits = hook._get_commits(head, base)
        lignes = hook._get_diff_lines(head, base)
    except subprocess.CalledProcessError:
        print("Contrôle des termes interdits impossible : PR refusée.", file=sys.stderr)
        return 1
    violations = hook.verifier(commits=commits, lignes_ajoutees=lignes, patterns=patterns)
    for champ, source in (("PR_TITLE", "pr:titre"), ("PR_BODY", "pr:corps")):
        if hook._contient_terme(os.environ.get(champ, ""), patterns):
            violations.append(hook.Violation(source=source))
    for violation in violations:
        print(f"Terme interdit détecté : {violation.source}", file=sys.stderr)
    if violations:
        return 1
    print(f"Aucun terme interdit ({len(patterns)} terme(s) contrôlé(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
