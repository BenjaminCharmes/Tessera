"""Measure what headroom removes from the inputs of the agents (ticket-605).

Run from `backend/`, in a throwaway environment (headroom is not a dependency):

    uv run --with headroom-ai python ../scripts/mesurer_compression.py \\
        --db tessera.db --runs <run_a> <run_b> --run-rouge <run_b> \\
        --sortie-test sortie_rouge.txt

`--sortie-test` is the output of `scripts/verifier.py` captured by hand in a
disposable worktree holding one red test: this script creates no worktree.
Without `--ecrire` the blocks are printed; with it, only the text between the
`mesure-605` markers of the spec is rewritten.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mesure_calculs import (
    ReleveRole,
    cout_retire,
    estimer_tokens,
    lignes_perdues,
    raison_non_mesurable,
    releve_par_role,
)
from mesure_headroom import (
    Compresseur,
    CompresseurIndisponible,
    compresser,
    diff_du_run,
    taux_retire,
)
from mesure_rendu import (
    MARQUEUR_CONCLUSION,
    MARQUEUR_DIFF,
    MARQUEUR_TABLEAU,
    MARQUEUR_USAGE,
    LigneDiff,
    LigneTableau,
    ecrire_blocs,
    rendre_conclusion,
    rendre_diffs,
    rendre_tableau,
)
from mesure_verdict import Mesures, verdict

_RACINE = Path(__file__).resolve().parent.parent
_SPEC = _RACINE / "docs/superpowers/specs/2026-10-27-compression-contexte-design.md"
_TEXTES_PAR_ROLE: dict[str, tuple[str, ...]] = {
    "reviewer": ("diff", "tests"),
    "securite": ("diff",),
    "doc-technique": ("diff",),
    "doc-fonctionnelle": ("diff",),
    "validateur": ("diff",),
}
_SANS_TEXTE = "prompts non stockés : lectures d'outils, hors du chemin texte"


def ligne_du_role(
    run: str, releve: ReleveRole, textes: dict[str, str], compresseur: Compresseur,
    raison_diff: str = "",
) -> LigneTableau:
    """One table row: the measured input and the estimate after compression."""
    entree = releve.input_tokens + releve.cache_read_tokens + releve.cache_creation_tokens
    genres = _TEXTES_PAR_ROLE.get(releve.role)
    if genres is None:
        return LigneTableau(run, releve.role, entree, None, None, _SANS_TEXTE)
    voulus = [textes[g] for g in genres if g in textes]
    if not voulus:
        raison = raison_diff or "diff du run indisponible"
        return LigneTableau(run, releve.role, entree, None, None, raison)
    try:
        compresses = [compresseur(t) for t in voulus]
    except CompresseurIndisponible as erreur:
        return LigneTableau(run, releve.role, entree, None, None, str(erreur))
    retires = sum(
        max(0, estimer_tokens(o) - estimer_tokens(c)) for o, c in zip(voulus, compresses)
    )
    perdues = _perdues(textes, genres, compresses)
    return LigneTableau(
        run, releve.role, entree, entree - retires, perdues, "",
        releve.cout_entree_usd, cout_retire(releve.modele, retires),
    )


def _perdues(textes: dict[str, str], genres: tuple[str, ...], compresses: list[str]) -> int | None:
    if "tests" not in textes or "tests" not in genres:
        return None
    voulus = [g for g in genres if g in textes]
    return len(lignes_perdues(textes["tests"], compresses[voulus.index("tests")]))


def ligne_du_diff(run: str, diff: str, raison: str, compresseur: Compresseur) -> LigneDiff:
    """The diff alone: its estimated tokens before and after compression."""
    if not diff:
        return LigneDiff(run, None, None, raison)
    try:
        compresse = compresseur(diff)
    except CompresseurIndisponible as erreur:
        return LigneDiff(run, estimer_tokens(diff), None, str(erreur))
    return LigneDiff(run, estimer_tokens(diff), estimer_tokens(compresse), "")


def agreger(
    lignes: list[LigneTableau], codeurs: list[ReleveRole], diffs: list[LigneDiff], runs: int
) -> Mesures:
    """Fold the rows into the figures the threshold reads."""
    texte = [x for x in lignes if x.role in ("reviewer", "securite") and x.apres is not None]
    cout = sum(x.cout_entree_usd for x in texte)
    ratio = sum(x.gain_usd for x in texte) / cout if cout > 0 else None
    perdues = [x.perdues for x in lignes if x.perdues is not None]
    total = sum(c.tokens_totaux for c in codeurs)
    entree = sum(c.input_tokens + c.cache_creation_tokens for c in codeurs)
    taux = [d.taux for d in diffs if d.taux is not None]
    return Mesures(
        runs, ratio, sum(perdues) if perdues else None,
        entree / total if total else None, max(taux) if taux else None,
    )


def _lire_texte(chemin: str | None) -> str:
    return Path(chemin).read_text(encoding="utf-8") if chemin else ""


def mesurer(
    args: argparse.Namespace, compresseur: Compresseur
) -> tuple[list[LigneTableau], list[LigneDiff], Mesures]:
    """Build the token rows, the diff rows and the aggregate for ``args.runs``."""
    db, lignes, diffs, codeurs = Path(args.db), [], [], []
    tests = _lire_texte(args.sortie_test)
    for run in args.runs:
        diff, raison_diff = diff_du_run(Path(args.repo), db, run, args.base)
        diffs.append(ligne_du_diff(run, diff, raison_diff, compresseur))
        raison = raison_non_mesurable(db, run)
        if raison:
            lignes.append(LigneTableau(run, "tous", None, None, None, raison))
            continue
        textes = {"diff": diff} if diff else {}
        if tests and run == args.run_rouge:
            textes["tests"] = tests
        for releve in releve_par_role(db, [run]).values():
            lignes.append(ligne_du_role(run, releve, textes, compresseur, raison_diff))
            if releve.role == "codeur":
                codeurs.append(releve)
    vus = {d.run for d in diffs if d.taux is not None} | {x.run for x in lignes if x.entree}
    return lignes, diffs, agreger(lignes, codeurs, diffs, len(vus))


def _analyser(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--run-rouge", default="")
    p.add_argument("--sortie-test", default=None)
    p.add_argument("--repo", default=str(_RACINE))
    p.add_argument("--base", default="develop")
    p.add_argument("--spec", default=str(_SPEC))
    p.add_argument("--ligne-usage", default="", help="line printed by sonde_usage.py")
    p.add_argument("--ecrire", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    """Measure, print the tables and the conclusion, optionally write the spec."""
    args = _analyser(argv)
    lignes, diffs, mesures = mesurer(args, compresser)
    blocs = {
        MARQUEUR_TABLEAU: rendre_tableau(lignes),
        MARQUEUR_DIFF: rendre_diffs(diffs),
        MARQUEUR_CONCLUSION: rendre_conclusion(verdict(mesures), mesures),
    }
    if args.ligne_usage:
        blocs[MARQUEUR_USAGE] = f"`{args.ligne_usage}`"
    sys.stdout.write("\n\n".join(blocs.values()) + "\n")
    if args.ecrire:
        ecrire_blocs(Path(args.spec), blocs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
