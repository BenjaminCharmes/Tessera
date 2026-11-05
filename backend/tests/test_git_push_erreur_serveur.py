"""A push refused by a GitHub server error is retried once, never forced (ticket-787)."""
import pytest

from tessera.services.git_workspace import GitCommandError, GitWorkspaceService

_SERVEUR = "remote: Internal Server Error\nfatal: unable to access: The requested URL returned error: 500"
_NON_FF = "! [rejected] b -> b (non-fast-forward)"


class _ServiceDouble(GitWorkspaceService):
    """Records every git call; push outcomes come from a scripted list."""

    def __init__(self, refus: list[str | None]) -> None:
        super().__init__(".")
        self._delai_reessai_serveur_s = 0.0
        self._refus = list(refus)
        self.appels: list[tuple[str, ...]] = []

    async def _run(self, *args: str) -> str:
        self.appels.append(args)
        if args[0] == "push":
            stderr = self._refus.pop(0)
            if stderr is not None:
                raise GitCommandError(["git", *args], 1, stderr)
            return ""
        if args[0] == "ls-remote":
            return ""  # distant sans la branche : jamais « à jour »
        raise GitCommandError(["git", *args], 1, "inconnu")

    def pushes(self) -> list[tuple[str, ...]]:
        return [a for a in self.appels if a[0] == "push"]


async def test_server_error_then_accepted_push_succeeds_in_two_calls() -> None:
    service = _ServiceDouble([_SERVEUR, None])

    await service.push_branch("b")

    assert len(service.pushes()) == 2


async def test_two_server_errors_in_a_row_raise_after_two_calls() -> None:
    service = _ServiceDouble([_SERVEUR, "remote: 502 Bad Gateway"])

    with pytest.raises(GitCommandError):
        await service.push_branch("b")

    assert len(service.pushes()) == 2


async def test_non_fast_forward_refusal_is_not_retried() -> None:
    service = _ServiceDouble([_NON_FF])

    with pytest.raises(GitCommandError):
        await service.push_branch("b")

    assert len(service.pushes()) == 1


async def test_no_call_carries_a_force_option() -> None:
    service = _ServiceDouble([_SERVEUR, None])

    await service.push_branch("b")

    for appel in service.appels:
        assert not any(a.startswith("--force") or a == "-f" for a in appel)
