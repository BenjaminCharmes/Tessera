"""A refused call closure must surface, not be swallowed (audit H2, ADR-037)."""
from typing import Any, cast

import pytest

from tessera.services.pipeline.etape_de_capture import _arreter
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.base import ProviderResult
from tessera.services.providers.droits_worktree import DroitsAgentRefuses


class _AppQuiEchoue:
    def __init__(self, erreur: Exception) -> None:
        self.erreur = erreur

    async def arreter(self) -> None:
        raise self.erreur


async def test_arreter_reraises_refused_rights() -> None:
    app = cast(Any, _AppQuiEchoue(DroitsAgentRefuses("profil non nettoyé")))
    with pytest.raises(DroitsAgentRefuses):
        await _arreter(app)


async def test_arreter_swallows_other_errors() -> None:
    app = cast(Any, _AppQuiEchoue(RuntimeError("boom")))
    await _arreter(app)


class _Fournisseur(ClaudeAgentSDKProvider):
    def __init__(self, echec: Exception) -> None:
        super().__init__()
        self.echec = echec
        self.appels: list[dict[str, Any]] = []

    async def _run(self, **kwargs: Any) -> ProviderResult:
        self.appels.append(kwargs)
        if "resume" in kwargs:
            raise self.echec
        return cast(ProviderResult, "neuf")


async def test_resume_reraises_refused_rights_without_fresh_call() -> None:
    provider = _Fournisseur(DroitsAgentRefuses("processus vivant"))
    with pytest.raises(DroitsAgentRefuses):
        await provider._run_ou_reprendre(session="s1", user="x")
    assert len(provider.appels) == 1


async def test_resume_other_error_starts_fresh_call() -> None:
    provider = _Fournisseur(RuntimeError("session introuvable"))
    resultat = await provider._run_ou_reprendre(session="s1", user="x")
    assert resultat == "neuf"
    assert len(provider.appels) == 2
