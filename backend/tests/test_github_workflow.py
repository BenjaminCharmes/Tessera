"""Agent de workflow GitHub — ticket-064."""
import json
from pathlib import Path

import pytest

from tessera.services.github_workflow import (
    GitHubWorkflowService,
    WorkflowError,
    build_pr_body,
)


class _FakeGit:
    def __init__(self, branch: str | None = "ticket-042-slug") -> None:
        self.branch = branch
        self.pushed: list[str] = []
        self.rebased: list[str] = []
        self.conflicts: list[str] = []

    async def push_branch(self, branch_name: str) -> None:
        self.pushed.append(branch_name)

    async def current_diff(self) -> str:
        return "diff --git a/x.py b/x.py\n+x = 1\n"

    #: Ce qui a été commité sur la branche : c'est ce qui part au push.
    diff_commite: str = "diff --git a/x.py b/x.py\n+x = 1\n"
    commits: list[object] = []

    async def diff_de_branche(self, base: str, branch: str) -> str:
        return self.diff_commite

    async def commits_depuis_base(self, base: str, branch: str) -> list[object]:
        return list(self.commits)


class _FakeStatut:
    def __init__(self, ci_status: str) -> None:
        self.ci_status = ci_status


class _FakeGitHub:
    def __init__(
        self,
        pr: tuple[int, str] = (7, "https://github.com/o/r/pull/7"),
        ci_status: str = "passing",
    ) -> None:
        self.pr = pr
        self.created: list[dict[str, object]] = []
        self.merged: list[int] = []
        self._ci_status = ci_status

    async def create_pull_request(self, **kwargs: object) -> tuple[int, str]:
        self.created.append(kwargs)
        return self.pr

    async def get_pull_request_status(self, pr_number: int) -> _FakeStatut:
        return _FakeStatut(self._ci_status)

    async def merge_pull_request(self, pr_number: int) -> None:
        self.merged.append(pr_number)


def _projet(tmp_path: Path, niveau: str | None) -> Path:
    """Un dossier de projet qui declare (ou non) son niveau d'autonomie."""
    racine = tmp_path / (niveau or "sans-declaration")
    racine.mkdir(parents=True, exist_ok=True)
    if niveau is not None:
        (racine / "agents.json").write_text(
            json.dumps({"autonomy": niveau}), encoding="utf-8"
        )
    return racine


def _ticket_body() -> str:
    return (
        "# ticket-042 — Endpoint de santé\n\n"
        "## Objectif\n\nExposer /health.\n\n"
        "## Critères d'acceptation\n\n- [ ] 200 sur /health\n"
    )


# ------------------------------------------------------------------
# Corps de la PR
# ------------------------------------------------------------------


def test_le_corps_de_pr_reprend_l_objectif_du_ticket() -> None:
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())

    assert "Exposer /health" in body
    assert "ticket-042" in body


def test_le_corps_de_pr_ne_porte_aucune_trace_d_ia() -> None:
    # ticket-060 : ce texte part dans le dépôt de l'utilisateur.
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())

    lowered = body.lower()
    for trace in ("co-authored-by", "claude", "generated with", "ia ", " ai "):
        assert trace not in lowered, trace


def test_le_corps_de_pr_reprend_les_criteres_d_acceptation() -> None:
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())
    assert "200 sur /health" in body


# ------------------------------------------------------------------
# Ouvrir une PR
# ------------------------------------------------------------------


async def test_pousse_la_branche_avant_d_ouvrir_la_pr(tmp_path: Path) -> None:
    # L'ordre est le correctif : GitHub refuse une `head` qu'il ne connaît pas.
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(git_workspace=git, github=github, base_branch="develop")

    result = await svc.open_pull_request(
        branch="ticket-042-slug",
        ticket_id="ticket-042",
        ticket_title="Endpoint de santé",
        ticket_body=_ticket_body(),
    )

    assert git.pushed == ["ticket-042-slug"]
    assert result.pr_number == 7
    assert github.created[0]["head"] == "ticket-042-slug"
    assert github.created[0]["base"] == "develop"


async def test_pr_title_carries_the_ticket_type(tmp_path: Path) -> None:
    # ADR-044 + ticket-259 : le titre de la PR suit la même convention que le
    # message de commit produit par pipeline_outcomes — préfixe Conventional
    # Commits.
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    await svc.open_pull_request(
        branch="ticket-123-slug",
        ticket_id="ticket-123",
        ticket_title="Add health endpoint",
        ticket_body="",
        ticket_type="feat",
    )

    assert github.created[0]["title"] == "feat: ticket-123 — Add health endpoint"


async def test_pr_title_without_type_keeps_legacy_format(tmp_path: Path) -> None:
    # Compatibilité ascendante : un appelant qui ne passe pas ticket_type obtient
    # le format historique (sans préfixe) plutôt qu'une chaîne malformée « : … ».
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    await svc.open_pull_request(
        branch="ticket-042-slug",
        ticket_id="ticket-042",
        ticket_title="Endpoint de santé",
        ticket_body=_ticket_body(),
    )

    assert github.created[0]["title"] == "ticket-042 — Endpoint de santé"


async def test_sans_branche_l_ouverture_est_refusee(tmp_path: Path) -> None:
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(), github=_FakeGitHub(), base_branch="develop"
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch=None, ticket_id="ticket-042", ticket_title="T", ticket_body=""
        )

    assert "branche" in str(exc.value).lower()


async def test_sans_github_configure_l_ouverture_est_refusee() -> None:
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(), github=None, base_branch="develop"
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="b", ticket_id="ticket-042", ticket_title="T", ticket_body=""
        )

    assert "github" in str(exc.value).lower()


# ------------------------------------------------------------------
# Ce que l'agent ne fait jamais
# ------------------------------------------------------------------


def test_le_merge_passe_toujours_par_la_porte(tmp_path: Path) -> None:
    """Le merge existe, mais aucun chemin n'y mène sans les deux conditions.

    ADR-022 ne tombe pas : elle devient conditionnelle (ADR-029). Le verrou
    n'est plus « aucun merge dans le code » mais « aucun merge qui ne passe
    pas par `peut_merger` », c'est-à-dire par une déclaration du projet **et**
    une CI verte.
    """
    import inspect

    from tessera.services import github_workflow

    source = inspect.getsource(github_workflow)
    lignes = [
        l for l in source.splitlines()
        if l.strip() and not l.strip().lstrip("#").strip().startswith(("#",))
        and not l.strip().startswith("#")
    ]
    appels = [l for l in lignes if "merge_pull_request" in l and "def " not in l]

    assert appels, "le merge doit exister pour être testable"
    for ligne in appels:
        assert "peut_merger" in source, "le merge doit être gardé par peut_merger"


def test_un_projet_sans_declaration_ne_merge_jamais(tmp_path: Path) -> None:
    from tessera.services.autonomie import peut_merger

    projet = tmp_path / "sans-declaration"
    projet.mkdir()

    assert peut_merger(projet, ci_status="passing") is False


# ------------------------------------------------------------------
# Jusqu'où le service va, projet par projet — ticket-082
# ------------------------------------------------------------------


async def test_un_projet_en_commit_refuse_de_pousser(tmp_path: Path) -> None:
    # Le cas des depots clients : l'utilisateur pousse lui-meme, parce que les
    # acces sont souvent specifiques. Un push parti tout seul n'est pas une
    # commodite, c'est une decision prise a sa place.
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "commit"),
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="b", ticket_id="ticket-042", ticket_title="T", ticket_body=""
        )

    assert git.pushed == []
    assert github.created == []
    assert "autonomy" in str(exc.value)


async def test_le_meme_projet_pousse_quand_l_humain_le_demande(
    tmp_path: Path,
) -> None:
    # Le reglage borne ce que l'IDE fait seul, pas ce que l'utilisateur peut
    # demander. Le bouton de l'IDE **est** sa decision.
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "commit"),
    )

    await svc.open_pull_request(
        branch="b",
        ticket_id="ticket-042",
        ticket_title="T",
        ticket_body="",
        autonome=False,
    )

    assert git.pushed == ["b"]


async def test_un_projet_en_pr_pousse_et_ouvre(tmp_path: Path) -> None:
    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    result = await svc.open_pull_request(
        branch="b", ticket_id="ticket-042", ticket_title="T", ticket_body=""
    )

    assert git.pushed == ["b"]
    assert result.pr_number == 7


async def test_le_merge_attend_une_ci_verte(tmp_path: Path) -> None:
    # Merger sur une CI rouge casserait la base de tous les tickets suivants,
    # et l'IDE perdrait le seul fait objectif sur lequel il s'appuie.
    github = _FakeGitHub(ci_status="failing")
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(),
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "merge"),
    )

    assert await svc.merge_si_la_ci_est_verte(7) is False
    assert github.merged == []


async def test_le_merge_a_lieu_quand_les_deux_conditions_tiennent(
    tmp_path: Path,
) -> None:
    github = _FakeGitHub(ci_status="passing")
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(),
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "merge"),
    )

    assert await svc.merge_si_la_ci_est_verte(7) is True
    assert github.merged == [7]


async def test_un_projet_en_pr_ne_merge_pas_meme_avec_une_ci_verte(
    tmp_path: Path,
) -> None:
    github = _FakeGitHub(ci_status="passing")
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(),
        github=github,
        base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    assert await svc.merge_si_la_ci_est_verte(7) is False
    assert github.merged == []


async def test_sans_projet_declare_rien_ne_merge(tmp_path: Path) -> None:
    # `project_path=None` est le cas des appels historiques : ils gardent le
    # comportement d'ADR-022, jamais de merge.
    github = _FakeGitHub(ci_status="passing")
    svc = GitHubWorkflowService(
        git_workspace=_FakeGit(), github=github, base_branch="develop"
    )

    assert await svc.merge_si_la_ci_est_verte(7) is False
    assert github.merged == []


# ------------------------------------------------------------------
# Refermer l'issue d'où vient le ticket — ticket-084
# ------------------------------------------------------------------


def test_le_corps_de_pr_referme_l_issue_d_origine() -> None:
    # Sans ce mot-clé, la boucle ne se referme pas : la PR est mergée et
    # l'issue reste ouverte, à refermer à la main.
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body(), issue=12)

    assert "Closes #12" in body


def test_sans_issue_le_corps_de_pr_ne_referme_rien() -> None:
    body = build_pr_body("ticket-042", "Endpoint de santé", _ticket_body())

    assert "Closes" not in body


async def test_la_pr_referme_l_issue_du_ticket(tmp_path: Path) -> None:
    from tessera.services.sync_map import SyncEntry, SyncMapService

    projet = _projet(tmp_path, "pr")
    SyncMapService().save(projet, {"ticket-042": SyncEntry(issue=12)})

    git, github = _FakeGit(), _FakeGitHub()
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=github,
        base_branch="develop",
        project_path=projet,
    )

    await svc.open_pull_request(
        branch="b", ticket_id="ticket-042", ticket_title="T", ticket_body=""
    )

    assert "Closes #12" in str(github.created[0]["body"])


# ------------------------------------------------------------------
# Termes interdits au push — ADR-048, ticket-206
# ------------------------------------------------------------------


def _avec_termes(monkeypatch: pytest.MonkeyPatch, termes: str) -> None:
    from tessera.config import settings

    monkeypatch.setattr(settings, "forbidden_terms", termes)


async def test_committed_content_with_a_forbidden_term_blocks_the_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Au push, tout est commité : l'arbre de travail est propre. C'est le
    # contenu des commits qui doit être lu, pas `current_diff`.
    _avec_termes(monkeypatch, "zorglub")
    git, github = _FakeGit(), _FakeGitHub()
    git.diff_commite = "diff --git a/n.md b/n.md\n+travail chez Zorglub\n"
    svc = GitHubWorkflowService(
        git_workspace=git, github=github, base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="ticket-042-slug", ticket_id="ticket-042",
            ticket_title="x", ticket_body=_ticket_body(),
        )

    assert git.pushed == []
    assert "zorglub" not in str(exc.value).lower()


async def test_a_manual_push_is_checked_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sans politique de run (bouton de l'IDE), la politique vient du manifeste :
    # ADR-048 dit « avant tout push ».
    _avec_termes(monkeypatch, "zorglub")
    git, github = _FakeGit(), _FakeGitHub()
    git.diff_commite = "diff --git a/n.md b/n.md\n+Zorglub\n"
    svc = GitHubWorkflowService(
        git_workspace=git, github=github, base_branch="develop",
        project_path=_projet(tmp_path, "pr"),
    )

    with pytest.raises(WorkflowError):
        await svc.open_pull_request(
            branch="ticket-042-slug", ticket_id="ticket-042",
            ticket_title="x", ticket_body=_ticket_body(), autonome=False,
        )
    assert git.pushed == []


async def test_a_professional_project_is_not_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _avec_termes(monkeypatch, "zorglub")
    racine = tmp_path / "pro"
    racine.mkdir()
    (racine / "agents.json").write_text(
        json.dumps({"autonomy": "pr", "confidentiality": "professional"}), encoding="utf-8"
    )
    git, github = _FakeGit(), _FakeGitHub()
    git.diff_commite = "diff --git a/n.md b/n.md\n+Zorglub\n"
    svc = GitHubWorkflowService(
        git_workspace=git, github=github, base_branch="develop", project_path=racine,
    )

    await svc.open_pull_request(
        branch="ticket-042-slug", ticket_id="ticket-042",
        ticket_title="x", ticket_body=_ticket_body(),
    )
    assert git.pushed == ["ticket-042-slug"]
