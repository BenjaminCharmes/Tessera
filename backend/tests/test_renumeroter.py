"""Un run renumérote avant livraison ce que `origin/develop` porte déjà — ticket-659.

Couverture :
- un `ticket-611` ajouté alors que la base porte un autre `ticket-611` passe au
  numéro libre suivant : nom du fichier, `id`, titre, `depends_on` et mentions
  sur les lignes ajoutées — une mention déjà sur la base ne bouge pas ;
- la même renumérotation pour une ADR ajoutée à `memory/decisions.md` ;
- chaque renumérotation écrit une ligne dans `memory/pipeline-log.md`, et la
  renumérotation est commitée ;
- un ticket qui change de dossier, une ADR qui passe à l'archive, un numéro
  libre : rien ne bouge, aucun commit ;
- l'étape de livraison passe avant le rebase, et un échec de lecture refuse.
"""
import json
from pathlib import Path

import pytest

from tests.depot_numerotation import creer_depot, ecrire, fiche, git
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.numerotation import GitIllisible
from tessera.services.renumeroter import Renumeroteur, renumeroter

_JOURNAL = "memory/pipeline-log.md"


def _branche_de_run(tmp_path: Path) -> Path:
    clone = creer_depot(tmp_path)
    git(clone, "checkout", "-q", "-b", "ticket-570-conception")
    return clone


def _commiter(clone: Path) -> None:
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "feat: work")


def _ajouter(clone: Path, chemin: str, texte: str) -> None:
    with (clone / chemin).open("a", encoding="utf-8", newline="\n") as f:
        f.write(texte)


def _ajouter_deux_fiches(clone: Path) -> None:
    ecrire(clone, "tickets/todo/ticket-611-nouveau.md", fiche(611, "nouveau"))
    ecrire(clone, "tickets/todo/ticket-612-suite.md", fiche(612, "suite", "[ticket-611]"))
    _ajouter(clone, "notes.md", "nouveau : ticket-611\n")
    _commiter(clone)


def test_ticket_added_with_a_number_taken_on_develop_takes_the_next_free_one(
    tmp_path: Path,
) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter_deux_fiches(clone)

    resultat = renumeroter(clone, "develop")

    assert [str(r) for r in resultat.renumerotations] == ["ticket-611 → ticket-613"]
    assert not (clone / "tickets/todo/ticket-611-nouveau.md").exists()
    nouvelle = (clone / "tickets/todo/ticket-613-nouveau.md").read_text(encoding="utf-8")
    assert "id: ticket-613" in nouvelle
    assert "# ticket-613 — nouveau" in nouvelle
    suite = (clone / "tickets/todo/ticket-612-suite.md").read_text(encoding="utf-8")
    assert "depends_on: [ticket-613]" in suite
    # Le ticket de la base ne bouge pas, ni la mention qu'elle porte déjà.
    assert (clone / "tickets/todo/ticket-611-deja-la.md").exists()
    notes = (clone / "notes.md").read_text(encoding="utf-8")
    assert notes == "ancien : ticket-611\nnouveau : ticket-613\n"


def test_added_adr_with_a_number_taken_on_develop_takes_the_next_free_one(
    tmp_path: Path,
) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter(clone, "memory/decisions.md", "\n## ADR-061 — Une autre décision\n\nVoir ADR-061 et ADR-001.\n")
    ecrire(clone, "tickets/todo/ticket-612-suite.md", fiche(612, "suite") + "Règle : ADR-061.\n")
    _commiter(clone)

    resultat = renumeroter(clone, "develop")

    assert [str(r) for r in resultat.renumerotations] == ["ADR-061 → ADR-062"]
    decisions = (clone / "memory/decisions.md").read_text(encoding="utf-8")
    assert "## ADR-061 — Base" in decisions
    assert "## ADR-062 — Une autre décision" in decisions
    assert "Voir ADR-062 et ADR-001." in decisions
    suite = (clone / "tickets/todo/ticket-612-suite.md").read_text(encoding="utf-8")
    assert "Règle : ADR-062." in suite


def test_every_renumbering_writes_a_line_in_the_pipeline_log(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter_deux_fiches(clone)
    _ajouter(clone, "memory/decisions.md", "\n## ADR-061 — Une autre décision\n")
    _commiter(clone)

    resultat = renumeroter(clone, "develop")

    lignes = (clone / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 2
    assert "ticket-611 → ticket-613" in lignes[0]
    assert "ADR-061 → ADR-062" in lignes[1]
    assert _JOURNAL in resultat.chemins


async def test_step_commits_the_renumbering_and_leaves_a_clean_tree(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter_deux_fiches(clone)

    faites = await Renumeroteur(GitWorkspaceService(clone), clone, "develop")()

    assert faites == ("ticket-611 → ticket-613",)
    message = git(clone, "log", "-1", "--format=%s")
    assert message == "chore: renumber the tickets and ADRs a run added"
    assert git(clone, "status", "--porcelain") == ""
    assert "tickets/todo/ticket-613-nouveau.md" in git(clone, "ls-files")


def test_nothing_moves_when_numbers_are_free_or_files_only_change_folder(
    tmp_path: Path,
) -> None:
    clone = _branche_de_run(tmp_path)
    git(clone, "mv", "tickets/todo/ticket-611-deja-la.md", "tickets/done/ticket-611-deja-la.md")
    ecrire(clone, "tickets/todo/ticket-700-libre.md", fiche(700, "libre"))
    _commiter(clone)

    resultat = renumeroter(clone, "develop")

    assert resultat.renumerotations == ()
    assert not (clone / _JOURNAL).exists()


def test_adr_moved_to_the_archive_unchanged_is_not_renumbered(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    ecrire(clone, "memory/decisions.md", "# Décisions\n\n## ADR-001 — Un\n")
    ecrire(clone, "memory/decisions-archive.md", "# Archive\n\n## ADR-061 — Base\n")
    _commiter(clone)

    assert renumeroter(clone, "develop").renumerotations == ()


def test_adr_whose_title_is_rewritten_is_not_renumbered(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    ecrire(clone, "memory/decisions.md", "# Décisions\n\n## ADR-001 — Un\n\n## ADR-061 — Base précisée\n")
    _commiter(clone)

    resultat = renumeroter(clone, "develop")

    assert resultat.renumerotations == ()
    assert not (clone / _JOURNAL).exists()
    assert "## ADR-061 — Base précisée" in (clone / "memory/decisions.md").read_text(encoding="utf-8")


def test_adr_duplicating_a_number_the_run_started_from_is_renumbered(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter(clone, "memory/decisions.md", "\n## ADR-061 — Un doublon\n")
    _commiter(clone)

    resultat = renumeroter(clone, "develop")

    assert [str(r) for r in resultat.renumerotations] == ["ADR-061 → ADR-062"]


def test_adr_added_before_develop_took_the_same_number_is_renumbered(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter(clone, "memory/decisions.md", "\n## ADR-062 — Celle du run\n")
    _commiter(clone)
    autre = tmp_path / "autre-develop"
    git(tmp_path, "clone", "-q", (tmp_path / "origin.git").as_uri(), str(autre))
    _ajouter(autre, "memory/decisions.md", "\n## ADR-062 — Celle de develop\n")
    _commiter(autre)
    git(autre, "push", "-q", "origin", "develop")
    git(clone, "fetch", "-q", "origin")

    resultat = renumeroter(clone, "develop")

    assert [str(r) for r in resultat.renumerotations] == ["ADR-062 → ADR-063"]
    decisions = (clone / "memory/decisions.md").read_text(encoding="utf-8")
    assert "## ADR-063 — Celle du run" in decisions


def test_unreadable_base_raises_instead_of_guessing(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter_deux_fiches(clone)
    git(clone, "remote", "remove", "origin")

    with pytest.raises(GitIllisible):
        renumeroter(clone, "develop")


class _FauxGit:
    def __init__(self) -> None:
        self.appels: list[str] = []

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        self.appels.append("sync")
        return None

    async def commit_bookkeeping(self) -> None:
        self.appels.append("bookkeeping")

    async def commits_hors_rangement(self, depuis: str) -> list[str]:
        return []

    async def rejouer_sur(self, base: str, resolveur: object = None) -> tuple[str, ...]:
        self.appels.append("rebase")
        return ()

    async def sha_distant(self, branch: str) -> str | None:
        return "a1" * 20


class _Ouverte:
    pr_number = 7


class _FauxWorkflow:
    def __init__(self) -> None:
        self.ouvertes = 0

    async def open_pull_request(self, **kwargs: object) -> _Ouverte:
        self.ouvertes += 1
        return _Ouverte()

    async def etat_ci(self, pr_number: int) -> str:
        return "passing"

    async def has_workflows(self) -> bool:
        return False

    async def pr_ouverte_de(self, branch: str) -> int | None:
        return None

    async def pr_state(self, pr_number: int) -> str:
        return "open"

    async def tete_pr(self, pr_number: int) -> str | None:
        return None

    async def merge_si_la_ci_est_verte(
        self, pr_number: int, sha_attendu: str | None = None
    ) -> bool:
        return False


async def _livrer(clone: Path, git_faux: _FauxGit, wf: _FauxWorkflow) -> Livraison:
    (clone / "agents.json").write_text(json.dumps({"autonomy": "pr"}), encoding="utf-8")
    service = LivraisonService(
        git_workspace=git_faux, workflow=wf, project_path=clone, base_branch="develop",
        renumeroter=Renumeroteur(GitWorkspaceService(clone), clone, "develop"),
    )
    return await service.livrer_phase_1(
        ticket_id="ticket-570", ticket_title="Conception", ticket_body="",
        branch="ticket-570-conception", approuve=True,
    )


async def test_delivery_renumbers_before_the_rebase_and_says_so(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    _ajouter_deux_fiches(clone)
    git_faux, wf = _FauxGit(), _FauxWorkflow()

    livraison = await _livrer(clone, git_faux, wf)

    assert livraison.etapes[0] == "renumérotation : ticket-611 → ticket-613"
    assert livraison.etapes[1] == "rebase sur develop"
    assert wf.ouvertes == 1
    assert (clone / "tickets/todo/ticket-613-nouveau.md").exists()


async def test_delivery_pushes_nothing_when_numbering_cannot_be_read(tmp_path: Path) -> None:
    clone = _branche_de_run(tmp_path)
    git(clone, "remote", "remove", "origin")
    git_faux, wf = _FauxGit(), _FauxWorkflow()

    livraison = await _livrer(clone, git_faux, wf)

    assert livraison.arret is not None
    assert "numérotation" in livraison.arret
    assert wf.ouvertes == 0
    assert "rebase" not in git_faux.appels
