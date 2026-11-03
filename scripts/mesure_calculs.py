"""Pure computations behind scripts/mesurer_compression.py (ticket-605).

Nothing here calls a model, headroom or git: the functions read a SQLite file,
compare two texts or apply the reopening threshold of the spec, so a test can
run them without any of the three.
"""
from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from tessera.services.cost_calculator import calculate_cost  # noqa: E402
from tessera.services.sortie_de_test import (  # noqa: E402
    extract_errors,
    extract_failure_details,
)

# Tarif d'écriture du cache : 1,25 x le tarif d'entrée (grille Anthropic). Le
# calculateur du backend l'ignore ; l'hypothèse est écrite ici et dans la spec.
FACTEUR_CREATION = 1.25
CARACTERES_PAR_TOKEN = 4


@dataclass(frozen=True)
class ReleveRole:
    """What `agent_calls` holds for one role over the chosen runs."""

    role: str
    modele: str
    appels: int
    input_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    output_tokens: int
    cout_entree_usd: float

    @property
    def tokens_totaux(self) -> int:
        return (
            self.input_tokens + self.cache_read_tokens
            + self.cache_creation_tokens + self.output_tokens
        )


def estimer_tokens(texte: str) -> int:
    """Approximate token count (characters / 4): no API key, no tokenizer."""
    return len(texte) // CARACTERES_PAR_TOKEN


def raison_non_mesurable(db_path: Path, run_id: str) -> str:
    """Why the run cannot be measured (column absent, or run before 604), or `""`."""
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as db:
        colonnes = {c[1] for c in db.execute("PRAGMA table_info(agent_calls)")}
        if "cache_creation_tokens" not in colonnes:
            return "colonne cache_creation_tokens absente (migration 9 non appliquée)"
        ligne = db.execute(
            "SELECT COALESCE(SUM(cache_creation_tokens), 0) FROM agent_calls"
            " WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if ligne and ligne[0] > 0:
        return ""
    return "antérieur au ticket-604 (cache créé non conservé)"


def run_mesurable(db_path: Path, run_id: str) -> bool:
    """True when the run's cache creation was kept (see `raison_non_mesurable`)."""
    return raison_non_mesurable(db_path, run_id) == ""


def _cout_entree(modele: str, entree: int, lu: int, cree: int) -> float:
    base = calculate_cost(modele, entree, 0, lu)
    return base + calculate_cost(modele, cree, 0, 0) * FACTEUR_CREATION


def releve_par_role(db_path: Path, run_ids: list[str]) -> dict[str, ReleveRole]:
    """Sum the token columns per role over ``run_ids`` (empty list: empty dict)."""
    if not run_ids:
        return {}
    marques = ",".join("?" for _ in run_ids)
    requete = (
        "SELECT role, model, COUNT(*), SUM(input_tokens), SUM(cache_read_tokens),"
        " SUM(cache_creation_tokens), SUM(output_tokens) FROM agent_calls"
        f" WHERE run_id IN ({marques}) GROUP BY role, model"
    )
    with sqlite3.connect(str(db_path)) as db:
        lignes = db.execute(requete, run_ids).fetchall()
    par_role: dict[str, ReleveRole] = {}
    for role, modele, appels, entree, lu, cree, sortie in lignes:
        cout = _cout_entree(modele, entree, lu, cree)
        existant = par_role.get(role)
        neuf = ReleveRole(role, modele, appels, entree, lu, cree, sortie, cout)
        par_role[role] = neuf if existant is None else _fusionner(existant, neuf)
    return par_role


def _fusionner(a: ReleveRole, b: ReleveRole) -> ReleveRole:
    """Sum a second model's line into a role; the busier model prices the rest."""
    return ReleveRole(
        a.role,
        a.modele if a.appels >= b.appels else b.modele,
        a.appels + b.appels,
        a.input_tokens + b.input_tokens,
        a.cache_read_tokens + b.cache_read_tokens,
        a.cache_creation_tokens + b.cache_creation_tokens,
        a.output_tokens + b.output_tokens,
        a.cout_entree_usd + b.cout_entree_usd,
    )


def cout_retire(modele: str, tokens: int) -> float:
    """Input price of ``tokens`` tokens removed (fresh-input rate: a ceiling)."""
    return calculate_cost(modele, tokens, 0, 0)


def lignes_perdues(original: str, compresse: str) -> list[str]:
    """Failure lines and test names of ``original`` absent from ``compresse``.

    Reads what the pipeline reads: `extract_errors` and
    `extract_failure_details`, plus every `FAILED` line.
    """
    attendues: list[str] = list(extract_errors(original, max_errors=10_000))
    for ligne in extract_failure_details(original, max_chars=10**9).splitlines():
        if ligne.strip():
            attendues.append(ligne.strip())
    for ligne in original.splitlines():
        if "FAILED" in ligne:
            attendues.append(ligne.strip())
    vues = dict.fromkeys(attendues)
    return [ligne for ligne in vues if ligne not in compresse]


def cellule(valeur: int | None, raison: str = "") -> str:
    """One table cell: a thousands-grouped number, or `non mesuré` + reason."""
    if valeur is None:
        return f"non mesuré ({raison})" if raison else "non mesuré"
    return f"{valeur:,}".replace(",", " ")
