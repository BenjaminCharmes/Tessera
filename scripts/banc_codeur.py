"""Replays the coder bench cells under a spending cap (ticket-1055, ADR-095).

Run from `backend/`:

    python ../scripts/banc_codeur.py rejouer --bras A --essai essai-1 --budget-usd 15

Copies live under `~/.tessera/banc-codeur/<essai>/<cellule>/`, never under
`IDE_WORKTREES_DIR`. The JSONL makes the run resumable: a cell already `ok` is
not replayed, and a different `gel_sha256` stops the script. No push, no PR.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from banc_codeur_bras import ESSAI, Bras, charger_bras, manifeste_temporaire
from banc_codeur_cellule import PLAFOND_CELLULE_USD, Resultat, Roles, lire_resultats, rejouer_cellule, vers_ligne
from banc_codeur_corpus import Corpus, charger, verifier

_RACINE = Path(__file__).resolve().parent.parent
_COPIES = Path.home() / ".tessera" / "banc-codeur"


class BudgetAtteint(RuntimeError):
    """The next cell could pass the cap: the replay stops, it does not truncate."""


class ResultatsIncompatibles(ValueError):
    """The results file was written for another freeze of the corpus."""


def verifier_gel(corpus: Corpus, existants: list[Resultat]) -> None:
    for r in existants:
        if r.gel_sha256 != corpus.gel_sha256:
            raise ResultatsIncompatibles(
                f"le fichier porte le gel {r.gel_sha256!r}, le corpus {corpus.gel_sha256!r}"
            )


def _verifier_budget(existants: list[Resultat], budget: float) -> None:
    depense = sum(r.cout_usd for r in existants)
    if depense + PLAFOND_CELLULE_USD > budget:
        raise BudgetAtteint(
            f"plafond de {budget:.2f} $ : {depense:.2f} $ consignés, une cellule peut coûter "
            f"{PLAFOND_CELLULE_USD:.2f} $"
        )


async def rejouer(
    corpus: Corpus, bras: Bras, roles: Roles, *, depot: Path, sortie: Path,
    racine_copies: Path, budget_usd: float,
) -> list[Resultat]:
    """Replays every entry of `bras` the file does not hold as `ok`; returns the new lines."""
    existants = lire_resultats(sortie)
    verifier_gel(corpus, existants)
    faits = {r.id for r in existants if r.bras == bras.id and r.etat == "ok"}
    nouveaux: list[Resultat] = []
    for entree in corpus.entrees:
        if entree.id in faits:
            continue
        _verifier_budget(existants + nouveaux, budget_usd)  # avant chaque cellule
        ligne = await rejouer_cellule(
            entree, bras.id, bras.modele, corpus.gel_sha256, roles,
            depot=depot, racine_copies=racine_copies,
        )
        sortie.parent.mkdir(parents=True, exist_ok=True)
        with sortie.open("a", encoding="utf-8") as fichier:
            fichier.write(vers_ligne(ligne) + "\n")
        nouveaux.append(ligne)
    return nouveaux


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = analyseur.add_subparsers(dest="commande", required=True)
    rejeu = sous.add_parser("rejouer", help="rejoue un bras sur le corpus")
    rejeu.add_argument("--bras", required=True)
    rejeu.add_argument("--essai", required=True, help="nom du dossier de copies")
    rejeu.add_argument("--budget-usd", type=float, required=True)
    rejeu.add_argument("--corpus", type=Path, default=ESSAI / "corpus.json")
    rejeu.add_argument("--sortie", type=Path, default=ESSAI / "resultats.jsonl")
    rejeu.add_argument("--depot", type=Path, default=_RACINE)
    return analyseur.parse_args(argv)


def main(
    argv: list[str] | None = None,
    construire: Callable[[Path, Bras], Roles] | None = None,
) -> int:
    args = _arguments(argv)
    corpus = charger(args.corpus)
    verifier(corpus)
    bras = next((b for b in charger_bras(ESSAI / "bras.json") if b.id == args.bras), None)
    if bras is None:
        raise SystemExit(f"bras inconnu : {args.bras}")
    if construire is None:
        from banc_codeur_roles import roles_reels
        construire = roles_reels
    with tempfile.TemporaryDirectory(prefix="banc-codeur-") as temporaire:
        dossier = manifeste_temporaire(bras, dossier=Path(temporaire))
        try:
            nouveaux = asyncio.run(rejouer(
                corpus, bras, construire(dossier, bras), depot=args.depot, sortie=args.sortie,
                racine_copies=_COPIES / args.essai, budget_usd=args.budget_usd,
            ))
        except (BudgetAtteint, ResultatsIncompatibles) as exc:
            print(exc, file=sys.stderr)
            return 2
    print(f"{len(nouveaux)} ligne(s) consignée(s) dans {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
