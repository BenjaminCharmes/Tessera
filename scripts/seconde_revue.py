"""Replays a reviewer on the second-review corpus, under a spending cap.

Ticket-844, ADR-079. Run from `backend/`:

    python ../scripts/seconde_revue.py rejouer --bras B
    python ../scripts/seconde_revue.py rejouer --bras C --candidat ollama:qwen3-coder:30b \
        --fenetre-caracteres N --budget-usd 10

Nothing here touches a run, a worktree or the manifest of ide-core: git is read
only, the manifest the provider is built from lives in a temporary folder, and
the results are appended to a JSONL file that makes the script resumable. The
product never imports this module.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from seconde_revue_corpus import Corpus, charger_corpus, diff_de
from seconde_revue_lecture import (
    Resultat,
    composer_entree,
    corps_du_ticket,
    leve,
    lire_resultats,
    remarques_au_seuil,
    vers_ligne,
)

from tessera.config import settings
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.verdicts.reviewer_schema import REVIEWER_SCHEMA
from tessera.services.verdicts.verdict_reviewer import _invalid_cause

_RACINE = Path(__file__).resolve().parent.parent
_ESSAI = _RACINE / "docs" / "essais" / "seconde-revue"
_PROMPT = _RACINE / "agents" / "prompts" / "reviewer.md"
_MANIFESTE_IDE = _RACINE / "projects" / "ide-core" / "agents.json"
_MAX_TOKENS = 8192
_ROLES = {"B": "reviewer", "C": "candidat"}


class BudgetAtteint(RuntimeError):
    """The next call could pass the cap: the replay stops, it does not truncate."""

    def __init__(self, depense: float, budget: float, restantes: int) -> None:
        super().__init__(
            f"plafond de {budget:.2f} $ atteint ({depense:.2f} $ consignés) : "
            f"{restantes} entrée(s) restent à rejouer"
        )
        self.restantes = restantes


class ResultatsIncompatibles(ValueError):
    """The results file was written for another freeze of the corpus."""


def agents_json_temporaire(dossier: Path, bras: str, provider: str, modele: str) -> Path:
    """Writes a one-role `agents.json` in `dossier` and returns that «project» folder.

    No `fallback` key: an unavailable candidate is recorded as such, another
    model never judges in its place (ADR-046).
    """
    dossier.mkdir(parents=True, exist_ok=True)
    role = {
        "role": _ROLES[bras], "model": modele, "max_tokens": _MAX_TOKENS,
        "prompt_file": str(_PROMPT), "provider": provider,
    }
    (dossier / "agents.json").write_text(
        json.dumps({"agents": [role]}, indent=2), encoding="utf-8"
    )
    return dossier


def _construire_par_role(dossier: Path, role: str) -> LLMProvider:
    return provider_pour_role(dossier, role, allow_tools=False)


def _depense(resultats: list[Resultat]) -> float:
    return sum(r.cout_usd for r in resultats)


def _ligne(corpus: Corpus, ident: str, bras: str, modele: str, etat: Any, **reste: Any) -> Resultat:
    return Resultat(
        id=ident, bras=cast(Literal["B", "C"], bras), modele=modele, gel_sha256=corpus.gel_sha256, etat=etat,
        leve=reste.get("leve"), remarques=reste.get("remarques", ()),
        cout_usd=reste.get("cout_usd", 0.0), duree_ms=reste.get("duree_ms", 0),
    )


async def _appeler(
    provider: LLMProvider, systeme: str, entree: str, modele: str
) -> tuple[Any, float, int]:
    debut = time.monotonic()
    reponse = await provider.complete(
        system=systeme, user=entree, model=modele, max_tokens=_MAX_TOKENS,
        schema=REVIEWER_SCHEMA,
    )
    return reponse, float(reponse.cost_usd or 0.0), round((time.monotonic() - debut) * 1000)


async def _une_entree(
    provider: LLMProvider, corpus: Corpus, indice: int, bras: str, modele: str,
    systeme: str, entree: str,
) -> Resultat:
    ident = corpus.entrees[indice].id
    seuil = settings.reviewer_confidence_threshold
    try:
        reponse, cout, duree = await _appeler(provider, systeme, entree, modele)
    except ProviderIndisponible:
        return _ligne(corpus, ident, bras, modele, "indisponible")
    sortie = reponse.structured
    if sortie is None or _invalid_cause(sortie) is not None:
        return _ligne(corpus, ident, bras, modele, "hors_schema", cout_usd=cout, duree_ms=duree)
    return _ligne(
        corpus, ident, bras, modele, "ok", leve=leve(sortie, seuil),
        remarques=remarques_au_seuil(sortie, seuil), cout_usd=cout, duree_ms=duree,
    )


def _verifier_gel(corpus: Corpus, existants: list[Resultat]) -> None:
    for r in existants:
        if r.gel_sha256 != corpus.gel_sha256:
            raise ResultatsIncompatibles(
                f"le fichier de résultats porte le gel {r.gel_sha256!r}, "
                f"le corpus {corpus.gel_sha256!r} : c'est un autre essai"
            )


async def rejouer(
    corpus: Corpus, bras: str, provider: str, modele: str, *,
    depot: Path, racine_tickets: Path, sortie: Path,
    budget_usd: float, fenetre_caracteres: int | None,
    construire: Callable[[Path, str], LLMProvider] = _construire_par_role,
) -> list[Resultat]:
    """Replays every entry the results file does not hold yet; returns the new lines.

    Raises `BudgetAtteint` before a call that could pass the cap (the dearest
    call so far stands for the next one); lines already written stay.
    """
    existants = lire_resultats(sortie)
    _verifier_gel(corpus, existants)
    faits = {r.id for r in existants if r.bras == bras}
    restantes = [i for i, e in enumerate(corpus.entrees) if e.id not in faits]
    if provider == "ollama" and fenetre_caracteres is None:
        raise ValueError("un candidat ollama exige une fenêtre en caractères")
    systeme = _PROMPT.read_text(encoding="utf-8")
    nouveaux: list[Resultat] = []
    with tempfile.TemporaryDirectory(prefix="seconde-revue-") as temporaire:
        projet = agents_json_temporaire(Path(temporaire), bras, provider, modele)
        fournisseur = construire(projet, _ROLES[bras])
        for place, indice in enumerate(restantes):
            tout = existants + nouveaux
            pire = max((r.cout_usd for r in tout), default=0.0)
            if _depense(tout) + pire > budget_usd:
                raise BudgetAtteint(_depense(tout), budget_usd, len(restantes) - place)
            entree = corpus.entrees[indice]
            texte = composer_entree(
                corps_du_ticket(entree.ticket, racine_tickets), diff_de(entree, depot)
            )
            if fenetre_caracteres is not None and len(systeme) + len(texte) > fenetre_caracteres:
                ligne = _ligne(corpus, entree.id, bras, modele, "hors_fenetre")
            else:
                ligne = await _une_entree(fournisseur, corpus, indice, bras, modele, systeme, texte)
            with sortie.open("a", encoding="utf-8") as fichier:
                fichier.write(vers_ligne(ligne) + "\n")
            nouveaux.append(ligne)
    return nouveaux


def _lire_candidat(valeur: str) -> tuple[str, str]:
    provider, _, modele = valeur.partition(":")
    if not provider or not modele:
        raise SystemExit(f"--candidat attend « provider:modele », reçu : {valeur!r}")
    return provider, modele


def _reviewer_actuel() -> tuple[str, str]:
    """The provider and model ide-core declares for `reviewer` (read only)."""
    for role in json.loads(_MANIFESTE_IDE.read_text(encoding="utf-8-sig"))["agents"]:
        if role["role"] == "reviewer":
            return role.get("provider", "agent_sdk"), role["model"]
    raise SystemExit("ide-core ne déclare pas de rôle reviewer")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sous = analyseur.add_subparsers(dest="commande", required=True)
    rejeu = sous.add_parser("rejouer", help="rejoue un bras sur le corpus")
    rejeu.add_argument("--bras", choices=("B", "C"), required=True)
    rejeu.add_argument("--candidat", help="provider:modele du bras C")
    rejeu.add_argument("--fenetre-caracteres", type=int)
    rejeu.add_argument("--budget-usd", type=float, default=10.0)
    rejeu.add_argument("--corpus", type=Path, default=_ESSAI / "corpus.json")
    rejeu.add_argument("--sortie", type=Path, default=_ESSAI / "resultats.jsonl")
    rejeu.add_argument("--depot", type=Path, default=_RACINE)
    rejeu.add_argument(
        "--tickets", type=Path, default=_RACINE / "projects" / "ide-core" / "tickets"
    )
    return analyseur.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    if args.bras == "C":
        if not args.candidat:
            raise SystemExit("le bras C exige --candidat provider:modele")
        provider, modele = _lire_candidat(args.candidat)
    else:
        provider, modele = _reviewer_actuel()
    try:
        nouveaux = asyncio.run(rejouer(
            charger_corpus(args.corpus), args.bras, provider, modele,
            depot=args.depot, racine_tickets=args.tickets, sortie=args.sortie,
            budget_usd=args.budget_usd, fenetre_caracteres=args.fenetre_caracteres,
        ))
    except BudgetAtteint as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"{len(nouveaux)} ligne(s) consignée(s) dans {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
