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


@pytest.fixture(autouse=True)
def _singletons_propres() -> Iterator[None]:
    """Reset the process-wide registry and hub between tests — ticket-128.

    `RUN_REGISTRY` et `EVENT_HUB` vivent le temps du process, comme le verrou
    dont ils reprennent le rôle (ADR-038). En test, ce process porte toute la
    suite : un run qu'un test laisse ouvert occupe le projet du suivant, et
    un abonnement jamais fermé reçoit les événements des tests d'après. Les
    deux symptômes se lisent comme un échec du code testé.

    Les caches de parsing de ticket et de projet sont également vidés pour
    que les tests restent indépendants (ticket-352).
    """
    from tessera.services.event_hub import EVENT_HUB
    from tessera.services.run_registry import RUN_REGISTRY
    from tessera.services import ticket_service as _ts_module
    from tessera.services import project_loader as _pl_module
    from tessera.services import pr_status_cache as _prc_module

    yield
    RUN_REGISTRY._runs.clear()
    EVENT_HUB._abonnes.clear()
    _ts_module._ticket_cache.clear()
    _pl_module._project_cache.clear()
    _prc_module.clear_memory_cache()


@pytest.fixture(autouse=True)
def _aucun_terme_interdit_de_la_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Les tests ne lisent jamais la vraie liste de `.env` (ADR-048).

    Le service des termes interdits la lit par défaut : sans cette fixture, un
    test passerait ou échouerait selon la machine, et un message d'erreur
    pourrait citer un terme réel.
    """
    from tessera.config import settings

    monkeypatch.setattr(settings, "forbidden_terms", "")
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)


@pytest.fixture(autouse=True, scope="session")
def _pas_de_vrai_journal() -> Iterator[None]:
    """Keep the app's startup from attaching the real log file in tests.

    Chaque `TestClient(app)` exécute le `lifespan`, qui ajoutait au logger
    racine un gestionnaire sur `backend/logs/tessera.log`, jamais retiré : la
    suite y écrivait, en autant d'exemplaires que de démarrages, et faisait
    tourner les fichiers gardés pour la trace d'un vrai plantage
    (ticket-339). `configure_file_logging` reste testé directement, dans
    `test_logger.py`.
    """
    import tessera.main

    async def _aucun_run_solde(*_a: object, **_k: object) -> list[str]:
        return []

    async def _aucune_reprise(*_a: object, **_k: object) -> None:
        return None

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(tessera.main, "configure_file_logging", lambda *a, **k: None)
        # Le `lifespan` solde aussi les runs « en cours » de la base et remet
        # leurs dépôts d'aplomb (tickets 177, 369). En test, `settings` désigne
        # la vraie base et le vrai dossier des projets : quand le testeur du
        # pipeline lance cette suite, le run qui la lance est bien en cours, et
        # chaque `TestClient(app)` le soldait — puis, depuis le ticket-369,
        # commitait son travail et changeait de branche en plein run
        # (2026-10-07). Les deux fonctions restent testées directement, dans
        # `test_runs_orphelins.py` et `test_reprise_run_orphelin.py`.
        mp.setattr(tessera.main, "solder_les_runs_orphelins", _aucun_run_solde)
        mp.setattr(tessera.main, "reprendre_depots_orphelins", _aucune_reprise)
        yield
