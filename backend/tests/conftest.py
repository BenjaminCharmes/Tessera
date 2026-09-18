"""Shared pytest fixtures and environment probes."""
import os
import tempfile
from pathlib import Path

import pytest
from collections.abc import Iterator


def _symlinks_available() -> bool:
    """True when this process may actually create a directory symlink.

    On Windows, `os.symlink` needs either Developer Mode or elevation and
    otherwise fails with WinError 1314 — an environment limitation, not a
    defect in the code under test.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "target"
        target.mkdir()
        try:
            (root / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


SYMLINKS_AVAILABLE = _symlinks_available()

requires_symlinks = pytest.mark.skipif(
    not SYMLINKS_AVAILABLE,
    reason=(
        "this process cannot create symlinks "
        f"(on {os.name}, enable Developer Mode or run elevated)"
    ),
)


@pytest.fixture(autouse=True)
def _prompts_du_depot_intacts() -> Iterator[None]:
    """Refuse qu'un test écrive dans les prompts livrés avec le dépôt.

    Panne vécue : `test_create_project_utilise_un_provider_sans_outils`
    appelait `create_project` sans rediriger `settings.ide_prompts_dir`.
    `_auto_create_missing_agents` écrivait donc dans le **vrai**
    `agents/prompts/`, recréant `orchestrateur.md` après sa suppression et
    écrasant son contenu par « un system prompt d'agent bootstrap ».

    Le garde compare l'empreinte du dossier avant et après. Il nomme le test
    fautif, là où le symptôme — un fichier modifié dans `git status` — était
    silencieux et attribué à personne.
    """
    dossier = Path(__file__).resolve().parents[2] / "agents" / "prompts"

    def empreinte() -> dict[str, int]:
        if not dossier.is_dir():
            return {}
        return {f.name: f.stat().st_size for f in dossier.glob("*.md")}

    avant = empreinte()
    yield
    apres = empreinte()
    if avant != apres:
        ajoutes = sorted(set(apres) - set(avant))
        retires = sorted(set(avant) - set(apres))
        modifies = sorted(n for n in set(avant) & set(apres) if avant[n] != apres[n])
        raise AssertionError(
            "ce test a écrit dans les prompts livrés avec le dépôt — "
            f"ajoutés {ajoutes}, retirés {retires}, modifiés {modifies}. "
            "Rediriger `settings.ide_prompts_dir` vers `tmp_path`."
        )
