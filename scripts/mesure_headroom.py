"""What touches headroom or git for scripts/mesurer_compression.py (ticket-605)."""
from __future__ import annotations

import importlib
import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path

from mesure_calculs import estimer_tokens

Compresseur = Callable[[str], str]


class CompresseurIndisponible(RuntimeError):
    """headroom is absent or does not answer in the shape this script reads."""


def compresser(texte: str) -> str:
    """Compress ``texte`` with headroom (late import: tests never load it).

    ``compress_user_messages=True`` is required: by default headroom leaves a
    user message untouched (`router:protected:user_message`), and a diff put in
    a prompt is a user message. Without it the script would measure a false 0 %.
    """
    try:
        module = importlib.import_module("headroom")
    except ImportError as erreur:
        raise CompresseurIndisponible(f"headroom absent : {erreur}") from erreur
    compress = getattr(module, "compress", None)
    if not callable(compress):
        raise CompresseurIndisponible("headroom n'expose pas compress()")
    resultat = compress([{"role": "user", "content": texte}], compress_user_messages=True)
    messages = getattr(resultat, "messages", None)
    dernier = messages[-1] if isinstance(messages, list) and messages else None
    contenu = dernier.get("content") if isinstance(dernier, dict) else None
    if not isinstance(contenu, str):
        raise CompresseurIndisponible("réponse de headroom illisible")
    return contenu


def taux_retire(original: str, compresse: str) -> float:
    """Share of the estimated tokens removed from ``original`` (0 when empty)."""
    avant = estimer_tokens(original)
    return max(0, avant - estimer_tokens(compresse)) / avant if avant else 0.0


def diff_du_run(depot: Path, db: Path, run_id: str, base: str) -> tuple[str, str]:
    """Return ``(diff, "")`` of the run's pushed commit, or ``("", reason)``."""
    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as con:
        ligne = con.execute(
            "SELECT pushed_sha FROM pipeline_runs WHERE id = ?", (run_id,)
        ).fetchone()
    if not ligne or not ligne[0]:
        return "", "pas de pushed_sha pour ce run"
    sha = str(ligne[0])
    racine = subprocess.run(
        ["git", "-C", str(depot), "merge-base", sha, base],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if racine.returncode != 0:
        return "", f"commit {sha[:8]} introuvable localement"
    rendu = subprocess.run(
        ["git", "-C", str(depot), "diff", racine.stdout.strip(), sha],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    return (rendu.stdout, "") if rendu.returncode == 0 else ("", "git diff a échoué")
