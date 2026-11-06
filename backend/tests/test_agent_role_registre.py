"""`AgentRole` only names roles the agent registry knows.

The only role allowed outside the registry is `github-sync`, a service role
excluded from it on purpose (the former `orchestrateur` had no prompt).
"""

from tessera.models.agent import AgentRole
from tessera.services.agents.agent_registry import AgentRegistryService

ROLE_DE_SERVICE = "github-sync"


def _roles_inconnus(valeurs: set[str]) -> list[str]:
    admis = AgentRegistryService.BUILTIN_ROLES | {ROLE_DE_SERVICE}
    return sorted(valeurs - admis)


def test_every_agent_role_is_in_the_registry_or_is_github_sync() -> None:
    valeurs = {role.value for role in AgentRole}

    assert _roles_inconnus(valeurs) == []


def test_check_rejects_a_role_unknown_to_the_registry() -> None:
    # Garde le test précédent honnête : une valeur périmée doit bien le faire échouer.
    assert _roles_inconnus({"codeur", "orchestrateur"}) == ["orchestrateur"]


def test_github_sync_is_the_only_role_outside_the_registry() -> None:
    valeurs = {role.value for role in AgentRole}

    hors_registre = valeurs - AgentRegistryService.BUILTIN_ROLES

    assert hors_registre <= {ROLE_DE_SERVICE}


def test_orchestrateur_is_no_longer_an_agent_role() -> None:
    assert "orchestrateur" not in {role.value for role in AgentRole}
