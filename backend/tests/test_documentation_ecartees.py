"""In the corrective round, a refused proof check drops one edition only — ticket-1036."""
import json
from pathlib import Path

import pytest

from tessera.services.documentation.documentation import EditionRefusee
from tessera.services.documentation.documentation_editions import appliquer_editions
from tests.test_documentation_preuve import _doc, _edition, _matiere, _Provider, _service

_CODE = "def connue()"


def _deux_editions(tmp_path: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    a = _doc(tmp_path, "Avant A.\n", "a.md")
    b = _doc(tmp_path, "Avant B.\n", "b.md")
    editions = [
        _edition("Avant A.", "Voir ADR-999.", _CODE, "a.md"),
        _edition("Avant B.", "Après B.", _CODE, "b.md"),
    ]
    return a, b, editions


def test_a_refused_edition_is_dropped_alone_when_a_list_is_given(tmp_path: Path) -> None:
    a, b, editions = _deux_editions(tmp_path)
    ecartees: list[str] = []

    ecrits = appliquer_editions(tmp_path, editions, matiere=_matiere(_CODE), ecartees=ecartees)

    assert ecrits == [str(b)]
    assert a.read_text(encoding="utf-8") == "Avant A.\n"
    assert "Après B." in b.read_text(encoding="utf-8")
    assert len(ecartees) == 1 and "ADR-999" in ecartees[0]


def test_without_the_list_the_first_refusal_raises_and_nothing_is_written(tmp_path: Path) -> None:
    a, b, editions = _deux_editions(tmp_path)

    with pytest.raises(EditionRefusee):
        appliquer_editions(tmp_path, editions, matiere=_matiere(_CODE))

    assert a.read_text(encoding="utf-8") == "Avant A.\n"
    assert b.read_text(encoding="utf-8") == "Avant B.\n"


def test_a_file_outside_the_documentation_still_raises_with_the_list(tmp_path: Path) -> None:
    _, _, editions = _deux_editions(tmp_path)
    hors: dict[str, object] = {"fichier": "src/a.py", "ancien": "x", "nouveau": "y"}

    with pytest.raises(EditionRefusee, match="n'est pas de la documentation"):
        appliquer_editions(
            tmp_path, [editions[1], hors], matiere=_matiere(_CODE), ecartees=[]
        )


async def test_the_service_keeps_the_valid_edition_and_reports_the_refused_one(
    tmp_path: Path,
) -> None:
    a, b, editions = _deux_editions(tmp_path)
    premier = json.dumps({"editions": [_edition("Avant A.", "Après A.", None, "a.md")]})
    correction = json.dumps({"editions": [
        _edition("Avant A.", "Voir ADR-999.", "code de ticket-001", "a.md"),
        _edition("Avant B.", "Après B.", "code de ticket-001", "b.md"),
    ]})
    service, provider = _service(tmp_path, [premier, correction, '{"editions": []}'])
    assert isinstance(provider, _Provider)

    resultat = await service.mettre_a_jour(tmp_path)

    assert resultat.tour_de_correction is True
    assert str(b) in resultat.fichiers_modifies
    assert any("ADR-999" in motif for motif in resultat.refus)
    assert a.read_text(encoding="utf-8") == "Avant A.\n"
    assert resultat.abandonnes == []
    marqueur = json.loads((tmp_path / "memory" / "documentation.json").read_text(encoding="utf-8"))
    assert "ticket-001" in marqueur["documentes"]
