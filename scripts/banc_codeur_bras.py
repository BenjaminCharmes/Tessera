"""Arms of the coder bench and their temporary manifest (ticket-1054, ADR-095).

An arm is a model plus a prompt, declared in `docs/essais/banc-codeur/bras.json`.
`manifeste_temporaire` writes a throwaway project folder (manifest, prompts,
skills) so that `provider_pour_role` resolves everything there: nothing of
ide-core is ever opened for writing. No model is called here.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tessera.services.providers.base import LLMProvider
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.par_role import provider_pour_role

_RACINE = Path(__file__).resolve().parent.parent
ESSAI = _RACINE / "docs" / "essais" / "banc-codeur"
PROJET_IDE = _RACINE / "projects" / "ide-core"
ROLES_COPIES = ("reviewer", "validateur", "testeur")
_PROMPT_CODEUR = "agents/prompts/codeur.md"


class BrasInvalide(ValueError):
    """`bras.json` is unreadable or an arm lacks a field."""


class BrasIndisponible(RuntimeError):
    """The arm's provider cannot be built; the bench records `indisponible`."""


@dataclass(frozen=True)
class Bras:
    """One arm: `prompt` is a path relative to the essay folder."""

    id: str
    modele: str
    provider: str
    prompt: str


def charger_bras(chemin: Path) -> list[Bras]:
    """Reads the arms of `chemin`; the prompt resolves next to that file."""
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
        bras = [Bras(**entree) for entree in brut["bras"]]
    except (OSError, ValueError, KeyError, TypeError) as erreur:
        raise BrasInvalide(f"{chemin} : {erreur}") from erreur
    if len({b.id for b in bras}) != len(bras):
        raise BrasInvalide(f"{chemin} : identifiant de bras en double")
    return bras


def _copier(source: Path, cible: Path) -> None:
    cible.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, cible)


def _roles(projet: Path) -> list[dict[str, Any]]:
    return list(json.loads((projet / "agents.json").read_text(encoding="utf-8"))["agents"])


def _role_codeur(bras: Bras, modele_ide: dict[str, Any]) -> dict[str, Any]:
    role = dict(modele_ide)
    role.update(model=bras.modele, provider=bras.provider, prompt_file=_PROMPT_CODEUR)
    role.pop("fallback", None)  # aucun repli : un bras indisponible se consigne (ADR-046)
    return role


def manifeste_temporaire(
    bras: Bras, projet: Path = PROJET_IDE, dossier: Path | None = None,
    essai: Path = ESSAI,
) -> Path:
    """Writes the arm's project folder in a new directory and returns it.

    `agents.json` holds the arm's `codeur` and the other roles of `projet`
    unchanged; prompts and the coder's skills are copied beside it.
    """
    racine = dossier if dossier is not None else Path(tempfile.mkdtemp(prefix="banc-codeur-"))
    racine.mkdir(parents=True, exist_ok=True)
    roles = _roles(projet)
    codeur = next(r for r in roles if r["role"] == "codeur")
    gardes = [r for r in roles if r["role"] in ROLES_COPIES]
    for role in gardes:
        _copier(_RACINE / role["prompt_file"], racine / role["prompt_file"])
    _copier(essai / bras.prompt, racine / _PROMPT_CODEUR)
    for skill in codeur.get("skills", []):
        source = projet / ".claude" / "skills" / skill / "SKILL.md"
        _copier(source, racine / ".claude" / "skills" / skill / "SKILL.md")
    manifeste = {"agents": [_role_codeur(bras, codeur), *gardes]}
    (racine / "agents.json").write_text(json.dumps(manifeste, indent=2), encoding="utf-8")
    return racine


def construire_provider(bras: Bras, dossier: Path) -> LLMProvider:
    """The provider of the arm's `codeur`; no fallback, a named error instead."""
    try:
        return provider_pour_role(dossier, "codeur")
    except ProviderIndisponible as erreur:
        raise BrasIndisponible(f"bras {bras.id} : {erreur}") from erreur
