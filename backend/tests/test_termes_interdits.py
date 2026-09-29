"""Contrôle des termes interdits avant push — ADR-048."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.politique_run import PolitiqueRun
from tessera.services.termes_interdits import (
    CommitInfo,
    TermesInterditsService,
    ViolationTerme,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service(terms: str, monkeypatch: pytest.MonkeyPatch) -> TermesInterditsService:
    """Instancie un service avec les termes donnés."""
    monkeypatch.setenv("FORBIDDEN_TERMS", terms)
    return TermesInterditsService()


def _diff_lines(path: str, content: str) -> list[str]:
    """Simule les lignes `+` d'un diff unifié pour un seul fichier."""
    return [f"+++ b/{path}", f"+{content}"]


def _commit(sha7: str, message: str, auteur: str = "Toto <t@t.local>") -> CommitInfo:
    return CommitInfo(sha7=sha7, message=message, auteur=auteur)


# ---------------------------------------------------------------------------
# TermesInterditsService — actif / inactif
# ---------------------------------------------------------------------------


def test_sans_variable_env_le_service_est_inactif(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)
    svc = TermesInterditsService()
    assert svc.actif is False


def test_liste_vide_rend_le_service_inactif(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _service("", monkeypatch)
    assert svc.actif is False


def test_liste_non_vide_rend_le_service_actif(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = _service("secret", monkeypatch)
    assert svc.actif is True


def test_service_inactif_renvoie_liste_vide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)
    svc = TermesInterditsService()
    violations = svc.verifier(
        lignes_ajoutees=["+++ b/x.py", "+secret content"],
        commits=[_commit("abc1234", "secret message")],
    )
    assert violations == []


# ---------------------------------------------------------------------------
# TermesInterditsService — détection
# ---------------------------------------------------------------------------


def test_detecte_terme_en_majuscules(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=_diff_lines("config.py", "HOST = 'ACME.internal'"),
        commits=[],
    )
    assert len(violations) == 1
    assert "file:config.py" in violations[0].source


def test_detecte_terme_accentue(monkeypatch: pytest.MonkeyPatch) -> None:
    # Terme stocké sans accent, texte avec accent : la normalisation NFKD
    # les rend identiques.
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=_diff_lines("readme.txt", "Ácmé organisation"),
        commits=[],
    )
    assert len(violations) == 1


def test_detecte_terme_avec_tiret(monkeypatch: pytest.MonkeyPatch) -> None:
    # "acme-corp" doit déclencher le terme "acme corp".
    svc = _service("acme corp", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=_diff_lines("deploy.sh", "host=acme-corp.example"),
        commits=[],
    )
    assert len(violations) == 1


def test_sous_chaine_ne_declenche_pas(monkeypatch: pytest.MonkeyPatch) -> None:
    # "acme" dans "subacme" ou "acmes" ne doit pas déclencher (mot entier).
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=_diff_lines("x.py", "subacme_prefix = True"),
        commits=[],
    )
    assert violations == []


def test_violation_ne_nomme_pas_le_terme(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _service("secret", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=_diff_lines("x.py", "password = secret"),
        commits=[],
    )
    assert violations
    assert "secret" not in violations[0].source


def test_une_seule_violation_par_fichier(monkeypatch: pytest.MonkeyPatch) -> None:
    # Plusieurs lignes avec le terme dans le même fichier → une seule violation.
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=[
            "+++ b/config.py",
            "+host = 'acme.internal'",
            "+backup = 'acme-backup.internal'",
        ],
        commits=[],
    )
    assert len(violations) == 1
    assert violations[0].source == "file:config.py"


# ---------------------------------------------------------------------------
# TermesInterditsService — commits
# ---------------------------------------------------------------------------


def test_detecte_terme_dans_message_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=[],
        commits=[_commit("abc1234", "fix: connect to acme API")],
    )
    assert len(violations) == 1
    assert violations[0].source == "commit:abc1234"


def test_detecte_terme_dans_auteur_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _service("corp", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=[],
        commits=[_commit("abc1234", "chore: update deps", "Dev Corp <dev@example.com>")],
    )
    assert len(violations) == 1
    assert "commit:abc1234" in violations[0].source


def test_une_seule_violation_par_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    # Terme dans message ET auteur → une seule violation par commit.
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=[],
        commits=[_commit("abc1234", "fix acme bug", "ACME Dev <d@example.com>")],
    )
    assert len(violations) == 1
    assert violations[0].source == "commit:abc1234"


def test_violations_sur_plusieurs_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _service("acme", monkeypatch)
    violations = svc.verifier(
        lignes_ajoutees=[],
        commits=[
            _commit("aaa1111", "feat: acme integration"),
            _commit("bbb2222", "fix: unrelated"),
            _commit("ccc3333", "chore: acme cleanup"),
        ],
    )
    sources = {v.source for v in violations}
    assert sources == {"commit:aaa1111", "commit:ccc3333"}


# ---------------------------------------------------------------------------
# PolitiqueRun — confidentialite
# ---------------------------------------------------------------------------


def _projet(tmp_path: Path, manifeste: dict[str, object] | None) -> Path:
    racine = tmp_path / "projet"
    racine.mkdir(parents=True, exist_ok=True)
    if manifeste is not None:
        (racine / "agents.json").write_text(
            json.dumps(manifeste), encoding="utf-8"
        )
    return racine


def test_confidentialite_lue_depuis_agents_json(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {"confidentiality": "professional"})
    politique = PolitiqueRun.lire(projet)
    assert politique.confidentialite == "professional"


def test_confidentialite_none_sans_declaration(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {})
    politique = PolitiqueRun.lire(projet)
    assert politique.confidentialite is None


def test_confidentialite_none_sans_agents_json(tmp_path: Path) -> None:
    projet = _projet(tmp_path, None)
    politique = PolitiqueRun.lire(projet)
    assert politique.confidentialite is None


def test_exempte_controle_termes_sur_projet_professional(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {"confidentiality": "professional"})
    politique = PolitiqueRun.lire(projet)
    assert politique.exempte_controle_termes is True


def test_non_exempte_sans_confidentiality(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {})
    assert PolitiqueRun.lire(projet).exempte_controle_termes is False


def test_non_exempte_avec_valeur_inconnue(tmp_path: Path) -> None:
    projet = _projet(tmp_path, {"confidentiality": "secret"})
    assert PolitiqueRun.lire(projet).exempte_controle_termes is False


def test_lire_ne_casse_pas_les_projets_existants(tmp_path: Path) -> None:
    # Un manifeste sans `confidentiality` doit continuer à fonctionner.
    projet = _projet(tmp_path, {"autonomy": "pr", "artifacts": "tracked"})
    politique = PolitiqueRun.lire(projet)
    assert politique.confidentialite is None
    assert politique.exempte_controle_termes is False


# ---------------------------------------------------------------------------
# GitHubWorkflowService — intégration du contrôle
# ---------------------------------------------------------------------------


class _FakeGit:
    def __init__(
        self,
        diff: str = "",
        commits: list[CommitInfo] | None = None,
    ) -> None:
        self._diff = diff
        self._commits = commits or []
        self.pushed: list[str] = []

    async def push_branch(self, branch_name: str) -> None:
        self.pushed.append(branch_name)

    async def current_diff(self) -> str:
        return self._diff

    async def diff_de_branche(self, base: str, branch: str) -> str:
        return self._diff

    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
        return self._commits


class _FakeGitHub:
    async def create_pull_request(self, **kwargs: object) -> tuple[int, str]:
        return 1, "https://github.com/o/r/pull/1"

    async def get_pull_request_status(self, pr_number: int) -> object:
        return object()

    async def merge_pull_request(self, pr_number: int) -> None:
        pass


class _FakeTermes:
    def __init__(self, violations: list[ViolationTerme]) -> None:
        self._violations = violations

    @property
    def actif(self) -> bool:
        return True

    def verifier(
        self,
        *,
        lignes_ajoutees: list[str],
        commits: list[CommitInfo],
    ) -> list[ViolationTerme]:
        return self._violations


def _svc(
    git: _FakeGit,
    termes: _FakeTermes | None = None,
    politique: PolitiqueRun | None = None,
) -> GitHubWorkflowService:
    """Service sans project_path : le contrôle d'autonomie est ignoré.

    Les tests de termes interdits n'ont pas à tester l'autonomie — un test
    dédié le fait dans test_github_workflow.py.
    """
    return GitHubWorkflowService(
        git_workspace=git,
        github=_FakeGitHub(),
        base_branch="develop",
        politique=politique,
        termes=termes,
    )


async def test_violation_dans_fichier_leve_workflow_error() -> None:
    git = _FakeGit()
    termes = _FakeTermes([ViolationTerme(source="file:src/config.py")])
    politique = PolitiqueRun(confidentialite=None)
    svc = _svc(git, termes=termes, politique=politique)

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="ticket-001-feature",
            ticket_id="t",
            ticket_title="T",
            ticket_body="",
            autonome=False,
        )

    assert "file:src/config.py" in str(exc.value)
    assert git.pushed == []


async def test_violation_dans_commit_leve_workflow_error() -> None:
    git = _FakeGit()
    termes = _FakeTermes([ViolationTerme(source="commit:abc1234")])
    politique = PolitiqueRun(confidentialite=None)
    svc = _svc(git, termes=termes, politique=politique)

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="ticket-001-feature",
            ticket_id="t",
            ticket_title="T",
            ticket_body="",
            autonome=False,
        )

    assert "commit:abc1234" in str(exc.value)
    assert git.pushed == []


async def test_projet_professionnel_court_circuite_le_controle() -> None:
    git = _FakeGit()
    termes = _FakeTermes([ViolationTerme(source="file:src/x.py")])
    politique = PolitiqueRun(confidentialite="professional")
    svc = _svc(git, termes=termes, politique=politique)

    # Aucune exception : le projet est exempté.
    await svc.open_pull_request(
        branch="ticket-001-feature",
        ticket_id="t",
        ticket_title="T",
        ticket_body="",
        autonome=False,
    )

    assert git.pushed == ["ticket-001-feature"]


async def test_service_sans_termes_ne_bloque_pas() -> None:
    git = _FakeGit()
    # `termes=None` : paramètre absent, appelants existants non cassés.
    svc = _svc(git, termes=None)

    await svc.open_pull_request(
        branch="ticket-001-feature",
        ticket_id="t",
        ticket_title="T",
        ticket_body="",
        autonome=False,
    )

    assert git.pushed == ["ticket-001-feature"]


async def test_sans_politique_le_controle_a_quand_meme_lieu() -> None:
    # Un push demandé depuis l'IDE n'a pas de politique figée : ADR-048 dit
    # « avant tout push », il est contrôlé comme les autres (ticket-206).
    git = _FakeGit()
    termes = _FakeTermes([ViolationTerme(source="file:x.py")])
    # politique=None
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=_FakeGitHub(),
        base_branch="develop",
        termes=termes,
    )

    with pytest.raises(WorkflowError):
        await svc.open_pull_request(
            branch="ticket-001-feature",
            ticket_id="t",
            ticket_title="T",
            ticket_body="",
            autonome=False,
        )

    assert git.pushed == []


async def test_aucune_violation_laisse_passer_le_push() -> None:
    git = _FakeGit()
    termes = _FakeTermes([])  # pas de violations
    politique = PolitiqueRun(confidentialite=None)
    svc = _svc(git, termes=termes, politique=politique)

    await svc.open_pull_request(
        branch="ticket-001-feature",
        ticket_id="t",
        ticket_title="T",
        ticket_body="",
        autonome=False,
    )

    assert git.pushed == ["ticket-001-feature"]


async def test_violation_le_terme_absent_du_message_d_erreur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le message de WorkflowError ne nomme pas le terme — ADR-048."""
    monkeypatch.setenv("FORBIDDEN_TERMS", "acme")
    git = _FakeGit(
        diff="+++ b/config.py\n+host = 'acme.internal'\n",
    )
    politique = PolitiqueRun(confidentialite=None)
    svc = GitHubWorkflowService(
        git_workspace=git,
        github=_FakeGitHub(),
        base_branch="develop",
        politique=politique,
        termes=TermesInterditsService(),
    )

    with pytest.raises(WorkflowError) as exc:
        await svc.open_pull_request(
            branch="b",
            ticket_id="t",
            ticket_title="T",
            ticket_body="",
            autonome=False,
        )

    assert "acme" not in str(exc.value)
    assert "file:config.py" in str(exc.value)


def test_the_service_reads_the_list_from_the_backend_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Le backend lit `.env` dans ses réglages sans l'exporter : le service doit
    # les lire, sinon il reste inactif en production (ticket-206).
    from tessera.config import settings
    from tessera.services.termes_interdits import TermesInterditsService

    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)
    monkeypatch.setattr(settings, "forbidden_terms", "zorglub")
    assert TermesInterditsService().actif
