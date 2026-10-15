"""A CI the token cannot read stops the delivery at once — ticket-449."""
import json
from pathlib import Path

from tessera.services.livraison import LivraisonService


class _FauxGit:
    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        return ()

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        return None

    async def commit_bookkeeping(self) -> None:
        pass


class _FauxWorkflow:
    def __init__(self, etat: str, code_http_ci: int | None = None) -> None:
        self._etat = etat
        self.code_http_ci = code_http_ci
        self.lectures_ci = 0
        self.merges: list[int] = []

    async def has_workflows(self) -> bool:
        return False

    async def pr_state(self, pr_number: int) -> str:
        return "open"

    async def open_pull_request(self, **kwargs: object) -> object:
        class _R:
            pr_number = 7
            pr_url = "https://github.com/o/r/pull/7"
            branch = "ticket-001-x"

        return _R()

    async def etat_ci(self, pr_number: int) -> str:
        self.lectures_ci += 1
        return self._etat

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        self.merges.append(pr_number)
        return True


class _Horloge:
    """Records every sleep instead of waiting."""

    def __init__(self) -> None:
        self.sommeils: list[float] = []

    async def __call__(self, secondes: float) -> None:
        self.sommeils.append(secondes)


def _service(
    tmp_path: Path, workflow: _FauxWorkflow, horloge: _Horloge
) -> LivraisonService:
    (tmp_path / "agents.json").write_text(
        json.dumps({"autonomy": "merge"}), encoding="utf-8"
    )
    return LivraisonService(
        git_workspace=_FauxGit(),
        workflow=workflow,
        project_path=tmp_path,
        base_branch="develop",
        attente_ci_max_s=900,
        intervalle_ci_s=10,
        grace_ci_s=20,
        dormir=horloge,
    )


async def test_attendre_la_ci_rend_unreadable_sans_dormir(tmp_path: Path) -> None:
    workflow = _FauxWorkflow("unreadable", 403)
    horloge = _Horloge()

    etat = await _service(tmp_path, workflow, horloge)._attendre_la_ci(7)

    assert etat == "unreadable"
    assert workflow.lectures_ci == 1
    assert horloge.sommeils == []


async def test_une_ci_illisible_arrete_la_livraison_sans_merger(
    tmp_path: Path,
) -> None:
    workflow = _FauxWorkflow("unreadable", 403)
    svc = _service(tmp_path, workflow, _Horloge())

    livraison = await svc.livrer_phase_2(7, ticket_id="ticket-001")

    assert workflow.merges == []
    assert livraison.merged is False
    assert livraison.pr_number == 7
    assert "Checks" in (livraison.arret or "")
    assert "403" in (livraison.arret or "")


async def test_une_ci_illisible_sans_code_connu_nomme_quand_meme_la_permission(
    tmp_path: Path,
) -> None:
    svc = _service(tmp_path, _FauxWorkflow("unreadable"), _Horloge())

    livraison = await svc.livrer_phase_2(7, ticket_id="ticket-001")

    assert "Checks" in (livraison.arret or "")
    assert "HTTP" not in (livraison.arret or "")


async def test_une_ci_sans_aucun_check_garde_le_delai_de_grace(
    tmp_path: Path,
) -> None:
    # Comportement inchangé : `none` se relit pendant la grâce (20 s, soit
    # deux pauses de 10 s), puis devient le verdict faute de workflow déclaré.
    workflow = _FauxWorkflow("none")
    horloge = _Horloge()

    etat = await _service(tmp_path, workflow, horloge)._attendre_la_ci(7)

    assert etat == "none"
    assert horloge.sommeils == [10, 10]
