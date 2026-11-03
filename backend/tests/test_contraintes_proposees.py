"""Une règle écrite par un agent attend l'accord humain — ticket-493."""
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.adr import adr_pertinents, contraintes_pour, lire_contraintes
from tessera.services.contraintes_touchees import lignes_hors_proposees
from tessera.services.pipeline_contraintes import arret_contraintes_hors_proposees
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun

_PROPOSEE = "- **Règle proposée par un run.** (ADR-099)"

_CONTRAINTES = f"""# Contraintes

Préambule.

## Proposées

Section ignorée par le chargeur.

{_PROPOSEE}

## Git

- **Règle universelle.** (ADR-027)

*(codeur)*

- **Règle du codeur.** (ADR-014)

## Langue

- **Anglais.** (ADR-044)
"""

_SANS_PROPOSEES = _CONTRAINTES.replace(
    f"## Proposées\n\nSection ignorée par le chargeur.\n\n{_PROPOSEE}\n\n", ""
)


# ------------------------------------------------------------------
# Le chargeur
# ------------------------------------------------------------------


@pytest.mark.parametrize("role", ["codeur", "reviewer", "architect", "inconnu"])
def test_proposed_section_reaches_no_role(role: str) -> None:
    rendu = contraintes_pour(_CONTRAINTES, role)

    assert "Règle proposée" not in rendu
    assert "Section ignorée" not in rendu
    assert "## Proposées" not in rendu


@pytest.mark.parametrize("role", ["codeur", "reviewer", "architect", "inconnu"])
def test_rest_of_file_is_unchanged_by_the_proposed_section(role: str) -> None:
    assert contraintes_pour(_CONTRAINTES, role) == contraintes_pour(_SANS_PROPOSEES, role)
    assert "Règle universelle" in contraintes_pour(_CONTRAINTES, role)


def test_scoped_rule_still_follows_its_role() -> None:
    assert "Règle du codeur" in contraintes_pour(_CONTRAINTES, "codeur")
    assert "Règle du codeur" not in contraintes_pour(_CONTRAINTES, "reviewer")


def test_loader_drops_proposed_section(tmp_path: Path) -> None:
    (tmp_path / "contraintes.md").write_text(_CONTRAINTES, encoding="utf-8")

    contexte = "## Décisions récentes\n" + lire_contraintes(tmp_path)

    assert "Règle proposée" not in lire_contraintes(tmp_path)
    assert "Règle proposée" not in adr_pertinents(contexte, "codeur")
    assert "Règle universelle" in adr_pertinents(contexte, "codeur")


# ------------------------------------------------------------------
# Le diff
# ------------------------------------------------------------------


def _diff(chemin: str, *blocs: tuple[int, list[str]]) -> str:
    """A unified diff made of `(first_line, [+added | -removed])` hunks."""
    texte = f"diff --git a/{chemin} b/{chemin}\n--- a/{chemin}\n+++ b/{chemin}\n"
    for debut, lignes in blocs:
        texte += f"@@ -{debut},0 +{debut},{len(lignes)} @@\n" + "\n".join(lignes) + "\n"
    return texte


def _ecrire(racine: Path, contenu: str, chemin: str = "memory/contraintes.md") -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(contenu, encoding="utf-8")


def test_line_added_under_proposed_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- nouvelle\n\n## Git\n\n- r\n")

    diff = _diff("memory/contraintes.md", (5, ["+- nouvelle"]))

    assert lignes_hors_proposees(diff, [tmp_path]) == []


def test_line_added_outside_proposed_is_reported(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n## Git\n\n- r\n- nouvelle\n")

    diff = _diff("memory/contraintes.md", (8, ["+- nouvelle"]))

    hors = lignes_hors_proposees(diff, [tmp_path])
    assert len(hors) == 1
    assert "nouvelle" in hors[0]


def test_line_added_before_any_section_is_reported(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n- nouvelle\n\n## Proposées\n")

    diff = _diff("memory/contraintes.md", (3, ["+- nouvelle"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


def test_line_removed_outside_proposed_is_reported(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- p\n\n## Git\n\n")

    diff = _diff("memory/contraintes.md", (9, ["-- règle retirée"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


def test_removed_section_header_is_reported(tmp_path: Path) -> None:
    # Retirer le titre rattacherait les règles de « Langue » à la section voisine.
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- p\n\n- anglais\n")

    diff = _diff("memory/contraintes.md", (7, ["-## Langue"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


def test_new_section_header_is_reported(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- p\n\n## Neuve\n\n- r\n")

    diff = _diff("memory/contraintes.md", (7, ["+## Neuve", "+", "+- r"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 2


def test_proposed_header_added_over_existing_rules_is_reported(tmp_path: Path) -> None:
    # Poser le titre au milieu avalerait les règles qui suivent.
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- règle existante\n\n## Git\n")

    diff = _diff("memory/contraintes.md", (3, ["+## Proposées"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


def test_proposed_section_created_with_its_content_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- nouvelle\n\n## Git\n")

    diff = _diff("memory/contraintes.md", (3, ["+## Proposées", "+", "+- nouvelle"]))

    assert lignes_hors_proposees(diff, [tmp_path]) == []


def test_blank_line_changes_are_ignored(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Git\n\n- r\n")

    diff = _diff("memory/contraintes.md", (4, ["+"]))

    assert lignes_hors_proposees(diff, [tmp_path]) == []


def test_other_files_are_not_concerned(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# D\n\n## ADR-001\n", "memory/decisions.md")

    diff = _diff("memory/decisions.md", (3, ["+## ADR-001"]))

    assert lignes_hors_proposees(diff, [tmp_path]) == []


def test_path_under_a_parent_repository_is_recognised(tmp_path: Path) -> None:
    chemin = "projects/ide-core/memory/contraintes.md"
    _ecrire(tmp_path, "# C\n\n## Git\n\n- r\n- nouvelle\n", chemin)

    diff = _diff(chemin, (6, ["+- nouvelle"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


def test_deleted_file_is_reported(tmp_path: Path) -> None:
    diff = _diff("memory/contraintes.md", (1, ["-# C"]))

    assert len(lignes_hors_proposees(diff, [tmp_path])) == 1


# ------------------------------------------------------------------
# Le run
# ------------------------------------------------------------------


class _Git:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def commit_all(self, message: str) -> str:
        self.messages.append(message)
        return "abc1234"


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    def __init__(self, git: _Git, projet: Path | None) -> None:
        self._git_workspace = git
        self._ticket_svc = _Tickets()
        self._project_path = projet
        self._max_review_rounds = 3
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(diff: str, events: list[OrchestratorEvent]) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(
        project_id="p",
        ticket=Ticket(
            id="ticket-001", title="T", type=TicketType.feat,
            status=TicketStatus.in_progress, priority=TicketPriority.medium,
            agent="codeur", body="",
        ),
        on_event=_on_event,
    )
    run.branch = "ticket-001-x"
    run.round_num = 1
    run.reviewed_code = diff
    return run


async def test_run_adding_a_rule_outside_proposed_is_blocked(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n## Git\n\n- r\n- nouvelle\n")
    events: list[OrchestratorEvent] = []
    git = _Git()
    orch = _Orch(git, tmp_path)
    run = _run(_diff("memory/contraintes.md", (8, ["+- nouvelle"])), events)

    resultat = await arret_contraintes_hors_proposees(orch, run)  # type: ignore[arg-type]

    assert resultat is not None
    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert resultat.commit_sha == "abc1234"
    assert "Proposées" in (resultat.arret or "")
    assert any("BLOCKED" in ligne and "nouvelle" in ligne for ligne in orch.logs)
    assert orch._ticket_svc.statut is TicketStatus.blocked
    raisons = [e.data.get("reason") for e in events if e.type is EventType.ERROR]
    assert "constraints_outside_proposed" in raisons


async def test_run_adding_a_rule_under_proposed_goes_on(tmp_path: Path) -> None:
    _ecrire(tmp_path, "# C\n\n## Proposées\n\n- nouvelle\n\n## Git\n\n- r\n")
    orch = _Orch(_Git(), tmp_path)
    run = _run(_diff("memory/contraintes.md", (5, ["+- nouvelle"])), [])

    assert await arret_contraintes_hors_proposees(orch, run) is None  # type: ignore[arg-type]
    assert orch.logs == []


async def test_run_without_a_project_path_goes_on() -> None:
    orch = _Orch(_Git(), None)
    run = _run(_diff("memory/contraintes.md", (1, ["+- x"])), [])

    assert await arret_contraintes_hors_proposees(orch, run) is None  # type: ignore[arg-type]


# ------------------------------------------------------------------
# Les consignes
# ------------------------------------------------------------------

_RACINE = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("prompt", ["architect", "codeur"])
def test_prompt_says_where_a_new_rule_is_written(prompt: str) -> None:
    texte = (_RACINE / "agents" / "prompts" / f"{prompt}.md").read_text(encoding="utf-8")

    assert "## Proposées" in texte
    assert "contraintes.md" in texte


def test_repository_constraints_file_has_its_proposed_section_and_rule() -> None:
    chemin = _RACINE / "projects" / "ide-core" / "memory" / "contraintes.md"
    texte = chemin.read_text(encoding="utf-8")

    assert "## Proposées" in texte
    # La section est ignorée du chargeur, mais la règle qui l'annonce est servie.
    assert "Cette section n'est injectée" not in contraintes_pour(texte, "codeur")
    assert "s'écrit sous `## Proposées`" in contraintes_pour(texte, "codeur")
