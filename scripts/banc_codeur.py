"""Replays the coder bench cells under a spending cap (ticket-1055, ADR-095).

Run from `backend/`:

    python ../scripts/banc_codeur.py rejouer --bras A --essai essai-1 --budget-usd 100
    python ../scripts/banc_codeur.py rejouer --pilote --budget-usd 15
    python ../scripts/banc_codeur.py reference

Copies live under `~/.tessera/banc-codeur/<essai>/<cellule>/`, never under
`IDE_WORKTREES_DIR`. The JSONL makes the run resumable: a cell already `ok` is
not replayed, and a different `gel_sha256` stops the script. No push, no PR.
The trial skips `pilote` entries; `--pilote` replays only them, on every arm,
entry by entry, into `resultats-pilote.jsonl` (ticket-1057). `reference` lays
the real diff on a base copy and runs the tests: the corpus keeps green ones.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from banc_codeur_bras import ESSAI, Bras, charger_bras, manifeste_temporaire
from banc_codeur_cellule import (
    PLAFOND_CELLULE_USD, Resultat, Roles, copier_sans_historique, lire_resultats, poser_solution,
    rejouer_cellule, vers_ligne,
)
from banc_codeur_corpus import Corpus, Entree, charger, verifier

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


async def _rejouer_cellules(
    corpus: Corpus, cellules: Sequence[tuple[Entree, Bras, Roles]], *, depot: Path,
    sortie: Path, racine_copies: Path, budget_usd: float,
) -> list[Resultat]:
    existants = lire_resultats(sortie)
    verifier_gel(corpus, existants)
    faits = {(r.id, r.bras) for r in existants if r.etat == "ok"}
    nouveaux: list[Resultat] = []
    for entree, bras, roles in cellules:
        if (entree.id, bras.id) in faits:
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


async def rejouer(
    corpus: Corpus, bras: Bras, roles: Roles, *, depot: Path, sortie: Path,
    racine_copies: Path, budget_usd: float, pilote: bool = False,
) -> list[Resultat]:
    """Replays every entry of `bras` the file does not hold as `ok`; returns the new lines.

    The trial replays the frozen entries only, `pilote=True` the pilot ones only.
    """
    cellules = [(e, bras, roles) for e in corpus.entrees if e.pilote == pilote]
    return await _rejouer_cellules(corpus, cellules, depot=depot, sortie=sortie,
                                   racine_copies=racine_copies, budget_usd=budget_usd)


async def rejouer_pilote(
    corpus: Corpus, paires: Sequence[tuple[Bras, Roles]], *, depot: Path, sortie: Path,
    racine_copies: Path, budget_usd: float,
) -> list[Resultat]:
    """Pilot entries times every arm, entry by entry, under one budget for the whole file."""
    cellules = [(e, b, r) for e in corpus.entrees if e.pilote for b, r in paires]
    return await _rejouer_cellules(corpus, cellules, depot=depot, sortie=sortie,
                                   racine_copies=racine_copies, budget_usd=budget_usd)


async def verifier_reference(entree: Entree, roles: Roles, *, depot: Path, cible: Path) -> str:
    """`vert`, `rouge` or `echec_env` for the real diff laid on a base copy."""
    copier_sans_historique(depot, entree.base_sha, cible)
    poser_solution(depot, entree, cible)
    if not await roles.env(cible):
        return "echec_env"
    return "vert" if await roles.tester(cible) else "rouge"


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = analyseur.add_subparsers(dest="commande", required=True)
    rejeu = sous.add_parser("rejouer", help="rejoue un bras sur le corpus, ou le pilote")
    rejeu.add_argument("--bras", help="obligatoire hors pilote ; le pilote prend tous les bras")
    rejeu.add_argument("--pilote", action="store_true", help="entrées pilote seules (ticket-1057)")
    rejeu.add_argument("--essai", help="nom du dossier de copies (défaut `pilote` avec --pilote)")
    rejeu.add_argument("--budget-usd", type=float, required=True)
    rejeu.add_argument("--sortie", type=Path, help="défaut resultats.jsonl ou resultats-pilote.jsonl")
    ref = sous.add_parser("reference", help="la vraie solution est-elle verte ?")
    ref.add_argument("--ids", nargs="*", help="défaut : les entrées pilote")
    for parseur in (rejeu, ref):
        parseur.add_argument("--corpus", type=Path, default=ESSAI / "corpus.json")
        parseur.add_argument("--depot", type=Path, default=_RACINE)
    args = analyseur.parse_args(argv)
    if args.commande == "rejouer":
        if not args.pilote and (args.bras is None or args.essai is None):
            analyseur.error("--bras et --essai sont obligatoires hors --pilote")
        args.essai = args.essai or "pilote"
        nom = "resultats-pilote.jsonl" if args.pilote else "resultats.jsonl"
        args.sortie = args.sortie or ESSAI / nom
    return args


async def _references(corpus: Corpus, roles: Roles, args: argparse.Namespace) -> int:
    ids = set(args.ids) if args.ids else {e.id for e in corpus.entrees if e.pilote}
    for entree in (e for e in corpus.entrees if e.id in ids):
        cible = _COPIES / "reference" / entree.id
        etat = await verifier_reference(entree, roles, depot=args.depot, cible=cible)
        print(f"{entree.id} {entree.ticket} {etat}", flush=True)
    return 0


def main(
    argv: list[str] | None = None,
    construire: Callable[[Path, Bras], Roles] | None = None,
) -> int:
    args = _arguments(argv)
    corpus = charger(args.corpus)
    verifier(corpus)
    tous = charger_bras(ESSAI / "bras.json")
    if args.commande == "rejouer" and not args.pilote:
        tous = [b for b in tous if b.id == args.bras]
        if not tous:
            raise SystemExit(f"bras inconnu : {args.bras}")
    if construire is None:
        from banc_codeur_roles import roles_reels
        construire = roles_reels
    with tempfile.TemporaryDirectory(prefix="banc-codeur-") as temporaire:
        paires = [
            (b, construire(manifeste_temporaire(b, dossier=Path(temporaire) / b.id), b))
            for b in tous
        ]
        if args.commande == "reference":
            return asyncio.run(_references(corpus, paires[0][1], args))
        try:
            if args.pilote:
                nouveaux = asyncio.run(rejouer_pilote(
                    corpus, paires, depot=args.depot, sortie=args.sortie,
                    racine_copies=_COPIES / args.essai, budget_usd=args.budget_usd,
                ))
            else:
                nouveaux = asyncio.run(rejouer(
                    corpus, paires[0][0], paires[0][1], depot=args.depot, sortie=args.sortie,
                    racine_copies=_COPIES / args.essai, budget_usd=args.budget_usd,
                ))
        except (BudgetAtteint, ResultatsIncompatibles) as exc:
            print(exc, file=sys.stderr)
            return 2
    print(f"{len(nouveaux)} ligne(s) consignée(s) dans {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
