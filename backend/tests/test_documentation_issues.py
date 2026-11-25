"""What each documentation role did, and why nothing was written — ticket-1037."""
import json
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.services.documentation.documentation import ResultatDocumentation
from tessera.services.documentation.documentation_reponse import donnees_de, lire_json
from tessera.services.documentation.documentation_selection import tickets_a_documenter
from tests.test_documentation import PREUVE, _avec_marqueur, _doc, _service, _ticket
from tests.test_documentation_apres_run import _runner
from tests.test_orchestrator import _FakeGit, _make_orchestrator, _noop

_EDITIONS = {"editions": [{"fichier": "docs/a.md", "apres_section": "## S", "texte": "x", "preuve": PREUVE}]}


def test_donnees_de_skips_prose_with_braces_before_the_json_block() -> None:
    contenu = "Je propose {fichier, extrait} ci-dessous.\n```json\n" + json.dumps(_EDITIONS) + "\n```"
    assert donnees_de(contenu, "doc-technique") == _EDITIONS


def test_donnees_de_keeps_the_first_fenced_block_that_is_a_json_object() -> None:
    contenu = "```\nnot {json}\n```\ntexte\n```json\n" + json.dumps(_EDITIONS) + "\n```"
    assert donnees_de(contenu, "doc-technique") == _EDITIONS


def test_lire_json_tells_unreadable_from_empty() -> None:
    assert lire_json("rien") is None
    assert lire_json('{"editions": []}') == {"editions": []}
    assert lire_json('  {"editions": []}  ') == {"editions": []}


async def test_unreadable_answer_is_a_refusal_naming_the_role(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    _avec_marqueur(tmp_path)
    svc, _ = _service(tmp_path, ["pas du json", "pas du json non plus"])
    resultat = await svc.mettre_a_jour(tmp_path)
    assert "doc-technique : réponse illisible" in resultat.refus
    assert resultat.issues["doc-technique"] == "réponse illisible"
    assert not resultat.fichiers_modifies
    assert [t.id for t in tickets_a_documenter(tmp_path)] == ["ticket-001"]


async def test_empty_correction_round_keeps_the_first_refusal(tmp_path: Path) -> None:
    _ticket(tmp_path, "ticket-001")
    _doc(tmp_path, "a.md", "# A\n\n## Existante\n\nc\n")
    _avec_marqueur(tmp_path)
    mauvaise = json.dumps(
        {"editions": [{"fichier": "docs/a.md", "apres_section": "## Absente", "texte": "x", "preuve": PREUVE}]}
    )
    svc, _ = _service(tmp_path, [mauvaise, '{"editions": []}', '{"editions": []}'])
    resultat = await svc.mettre_a_jour(tmp_path)
    assert resultat.tour_de_correction is True
    assert any(r.startswith("doc-technique : ") and "Absente" in r for r in resultat.refus)
    assert resultat.issues["doc-technique"] == "refusé"


async def test_journal_line_names_each_role_that_wrote_nothing(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path, runner=_runner(), git_workspace=_FakeGit())
    orc._documenter = AsyncMock(
        return_value=ResultatDocumentation(
            [], ["doc-technique : réponse illisible"], ["ticket-001"],
            issues={"doc-technique": "réponse illisible", "doc-fonctionnelle": "aucune édition proposée"},
        )
    )
    lignes: list[str] = []
    orc._log = lignes.append  # type: ignore[method-assign]
    await orc.run_pipeline("proj", "ticket-001", _noop)
    ligne = next(ln for ln in lignes if "documentation: 0 fichier(s)" in ln)
    assert "doc-technique : réponse illisible" in ligne
    assert "doc-fonctionnelle : aucune édition proposée" in ligne
