"""La description du projet s'écrit par le service, dans la seule clé — ticket-724.

Aucun agent n'écrit `agents.json` (ADR-027) : doc-technique propose un texte, le
service le contrôle (ADR-057) et ne remplace que la clé `description`.
"""
import json
from pathlib import Path

import pytest

from tessera.services.documentation import DocumentationService
from tessera.services.documentation_base import EditionRefusee
from tessera.services.documentation_code import DiffDeTicket, MatiereCode
from tessera.services.documentation_description import (
    LONGUEUR_MAX,
    ecrire_description,
    remplacer_description,
)
from tessera.services.documentation_preuve import ControleDePreuve
from tessera.services.providers.base import ProviderResult
from tests.matiere_factice import matiere_factice

_PREUVE = [{"fichier": "src/m.py", "extrait": "def decrire("}]


def _controle() -> ControleDePreuve:
    matiere = MatiereCode(
        diffs=[DiffDeTicket("ticket-001", "diff --git a/src/m.py b/src/m.py\n+def decrire(x):\n", ["src/m.py"])],
        fichiers=[],
        sans_diff=[],
    )
    return ControleDePreuve(matiere, "")


def _proposition(texte: str = "Un IDE qui orchestre des agents.") -> dict[str, object]:
    return {"texte": texte, "preuve": _PREUVE}


def test_description_rewrites_only_its_key(tmp_path: Path) -> None:
    manifeste = tmp_path / "agents.json"
    avant = (
        '﻿{\r\n  "project_id": "p",\r\n  "pipeline": {"description": "imbriquée"},\r\n'
        '  "description": "ancienne",\r\n  "agents": [ {"role": "codeur"} ]\r\n}\r\n'
    )
    manifeste.write_bytes(avant.encode("utf-8"))

    assert ecrire_description(manifeste, _proposition("Une é nouvelle."), _controle()) is True

    attendu = avant.replace('"description": "ancienne"', '"description": "Une é nouvelle."')
    assert manifeste.read_bytes() == attendu.encode("utf-8")
    assert json.loads(attendu.lstrip("﻿"))["pipeline"] == {"description": "imbriquée"}


def test_description_is_added_after_the_last_member(tmp_path: Path) -> None:
    manifeste = tmp_path / "agents.json"
    avant = '{\n  "project_id": "p",\n  "pipeline": {"description": "imbriquée"}\n}\n'
    manifeste.write_bytes(avant.encode("utf-8"))

    ecrire_description(manifeste, _proposition(), _controle())

    attendu = (
        '{\n  "project_id": "p",\n  "pipeline": {"description": "imbriquée"},\n'
        '  "description": "Un IDE qui orchestre des agents."\n}\n'
    )
    assert manifeste.read_text(encoding="utf-8") == attendu


def test_description_is_added_to_an_empty_object_and_to_compact_json() -> None:
    assert json.loads(remplacer_description("{}", "x")) == {"description": "x"}
    assert remplacer_description('{"a":1}', "x") == '{"a":1,"description": "x"}'


def test_description_already_written_leaves_the_file_alone(tmp_path: Path) -> None:
    manifeste = tmp_path / "agents.json"
    manifeste.write_text('{"description": "Un IDE qui orchestre des agents."}', encoding="utf-8")
    avant = manifeste.stat().st_mtime_ns

    assert ecrire_description(manifeste, _proposition(), _controle()) is False
    assert manifeste.stat().st_mtime_ns == avant


@pytest.mark.parametrize(
    "texte", ["x" * (LONGUEUR_MAX + 1), "Une ligne.\nEt une autre.", "Une ligne.\rEt.", "   "]
)
def test_description_over_220_chars_or_multiline_is_refused(tmp_path: Path, texte: str) -> None:
    manifeste = tmp_path / "agents.json"
    avant = '{\n  "description": "ancienne"\n}\n'
    manifeste.write_text(avant, encoding="utf-8")

    with pytest.raises(EditionRefusee):
        ecrire_description(manifeste, _proposition(texte), _controle())

    assert manifeste.read_text(encoding="utf-8") == avant


def test_description_of_exactly_220_chars_is_accepted(tmp_path: Path) -> None:
    manifeste = tmp_path / "agents.json"
    manifeste.write_text("{}", encoding="utf-8")

    ecrire_description(manifeste, _proposition("y" * LONGUEUR_MAX), _controle())

    assert json.loads(manifeste.read_text(encoding="utf-8"))["description"] == "y" * LONGUEUR_MAX


@pytest.mark.parametrize(
    "description",
    [
        {"texte": "Un IDE."},
        {"texte": "Un IDE.", "preuve": []},
        {"texte": "Un IDE.", "preuve": [{"fichier": "src/m.py", "extrait": "def inventee("}]},
        {"texte": "Un IDE.", "preuve": [{"fichier": "src/m.py", "extrait": ""}]},
        {"texte": "Un IDE d'après l'ADR-999.", "preuve": _PREUVE},
        "Un IDE.",
    ],
)
def test_description_without_proof_is_refused(tmp_path: Path, description: object) -> None:
    manifeste = tmp_path / "agents.json"
    avant = '{"description": "ancienne"}'
    manifeste.write_text(avant, encoding="utf-8")

    with pytest.raises(EditionRefusee):
        ecrire_description(manifeste, description, _controle())

    assert manifeste.read_text(encoding="utf-8") == avant


@pytest.mark.parametrize("contenu", ["pas du json", "[1, 2]"])
def test_description_in_an_unreadable_manifest_is_refused(tmp_path: Path, contenu: str) -> None:
    manifeste = tmp_path / "agents.json"
    manifeste.write_text(contenu, encoding="utf-8")

    with pytest.raises(EditionRefusee):
        ecrire_description(manifeste, _proposition(), _controle())

    assert manifeste.read_text(encoding="utf-8") == contenu


def test_description_of_a_missing_manifest_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EditionRefusee):
        ecrire_description(tmp_path / "agents.json", _proposition(), _controle())


class _Provider:
    def __init__(self, reponses: dict[str, str], role: str) -> None:
        self._reponses = reponses
        self._role = role

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> ProviderResult:
        return ProviderResult(content=self._reponses[self._role], input_tokens=0, output_tokens=0)


def _lot(tmp_path: Path, reponses: dict[str, str]) -> tuple[DocumentationService, Path]:
    projet = tmp_path / "projects" / "p"
    (projet / "memory").mkdir(parents=True)
    (projet / "memory" / "documentation.json").write_text('{"documentes": []}', encoding="utf-8")
    (projet / "tickets" / "done").mkdir(parents=True)
    (projet / "tickets" / "done" / "ticket-001-x.md").write_text(
        '---\ntitle: "x"\n---\n# x\n', encoding="utf-8"
    )
    (projet / "agents.json").write_text('{\n  "description": "ancienne"\n}\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("vieux texte\n", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text("sys", encoding="utf-8")
    service = DocumentationService(
        _Provider(reponses, "doc-technique"),  # type: ignore[arg-type]
        prompts,
        fournisseur=lambda role: (_Provider(reponses, role), None),  # type: ignore[arg-type,return-value]
        matiere=matiere_factice(),
    )
    return service, projet


_EDITION = {
    "fichier": "README.md",
    "ancien": "vieux texte",
    "nouveau": "texte neuf",
    "preuve": [{"fichier": "src/ticket-001.py", "extrait": "code de ticket-001"}],
}


def _reponse(description: dict[str, object] | None) -> str:
    donnees: dict[str, object] = {"editions": [_EDITION]}
    if description is not None:
        donnees["description"] = description
    return json.dumps(donnees)


async def test_a_refused_description_does_not_block_the_rest_of_the_batch(tmp_path: Path) -> None:
    trop_longue = {"texte": "x" * 300, "preuve": [{"fichier": "src/ticket-001.py", "extrait": "code de ticket-001"}]}
    service, projet = _lot(
        tmp_path, {"doc-technique": _reponse(trop_longue), "doc-fonctionnelle": '{"editions": []}'}
    )

    resultat = await service.mettre_a_jour(projet, racine_doc=tmp_path)

    assert (projet / "agents.json").read_text(encoding="utf-8") == '{\n  "description": "ancienne"\n}\n'
    assert any("description refusée" in r for r in resultat.refus)
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "texte neuf\n"
    assert resultat.tickets == ["ticket-001"]
    assert str(projet / "agents.json") not in resultat.fichiers_modifies


async def test_an_accepted_description_is_written_and_reported(tmp_path: Path) -> None:
    bonne = {"texte": "Un IDE de test.", "preuve": [{"fichier": "src/ticket-001.py", "extrait": "code de ticket-001"}]}
    service, projet = _lot(
        tmp_path, {"doc-technique": _reponse(bonne), "doc-fonctionnelle": '{"editions": []}'}
    )

    resultat = await service.mettre_a_jour(projet, racine_doc=tmp_path)

    attendu = '{\n  "description": "Un IDE de test."\n}\n'
    assert (projet / "agents.json").read_text(encoding="utf-8") == attendu
    assert str(projet / "agents.json") in resultat.fichiers_modifies
    assert resultat.refus == []


async def test_only_doc_technique_may_propose_a_description(tmp_path: Path) -> None:
    bonne = {"texte": "Un guide.", "preuve": [{"fichier": "src/ticket-001.py", "extrait": "code de ticket-001"}]}
    service, projet = _lot(
        tmp_path, {"doc-technique": '{"editions": []}', "doc-fonctionnelle": _reponse(bonne)}
    )

    await service.mettre_a_jour(projet, racine_doc=tmp_path)

    assert "ancienne" in (projet / "agents.json").read_text(encoding="utf-8")
