"""Each documentation role reads the disk as it is at its call — ticket-962."""
import json
from pathlib import Path

from tessera.services.documentation import documentation as module
from tessera.services.documentation.documentation import DocumentationService
from tests.matiere_factice import matiere_factice
from tests.test_documentation import PREUVE, _avec_marqueur, _doc, _ticket

GUIDE = "docs/guide-utilisateur.md"


def _edition(ancien: str, nouveau: str) -> str:
    edition = {"fichier": GUIDE, "ancien": ancien, "nouveau": nouveau, "preuve": PREUVE}
    return json.dumps({"editions": [edition]})


class _ParRole:
    """Provider answering from a per-role queue, recording every prompt."""

    def __init__(self, reponses: dict[str, list[str]]) -> None:
        self.reponses = reponses
        self.appels: list[tuple[str, str]] = []

    async def complete(self, **kwargs: object) -> object:
        role = str(kwargs["system"]).removeprefix("prompt ")
        self.appels.append((role, str(kwargs["user"])))
        file = self.reponses.get(role, [])

        class _R:
            content = file.pop(0) if file else '{"editions": []}'
            input_tokens = output_tokens = cache_read_tokens = 0
            cost_usd = 0.0

        return _R()


def _preparer(
    tmp_path: Path, reponses: dict[str, list[str]]
) -> tuple[DocumentationService, _ParRole, Path]:
    _ticket(tmp_path, "ticket-001")
    guide = _doc(tmp_path, "guide-utilisateur.md", "# Guide\n\nancien paragraphe\n")
    _avec_marqueur(tmp_path)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    for role in ("doc-technique", "doc-fonctionnelle"):
        (prompts / f"{role}.md").write_text(f"prompt {role}", encoding="utf-8")
    provider = _ParRole(reponses)
    service = DocumentationService(provider, prompts, matiere=matiere_factice())  # type: ignore[arg-type]
    return service, provider, guide


async def test_second_role_reads_text_written_by_first_role(tmp_path: Path) -> None:
    service, provider, guide = _preparer(tmp_path, {
        "doc-technique": [_edition("ancien paragraphe", "paragraphe remplace")],
        "doc-fonctionnelle": [_edition("paragraphe remplace", "paragraphe final")],
    })

    resultat = await service.mettre_a_jour(tmp_path)

    prompt = dict(provider.appels)["doc-fonctionnelle"]
    assert "paragraphe remplace" in prompt
    assert "ancien paragraphe" not in prompt
    assert "paragraphe final" in guide.read_text(encoding="utf-8")
    assert not resultat.refus


async def test_correction_round_prompt_carries_disk_content(tmp_path: Path) -> None:
    absent = _edition("texte absent", "x")
    service, provider, _ = _preparer(tmp_path, {
        "doc-technique": [_edition("ancien paragraphe", "paragraphe remplace")],
        "doc-fonctionnelle": [absent, absent],
    })

    await service.mettre_a_jour(tmp_path)

    prompts = [user for role, user in provider.appels if role == "doc-fonctionnelle"]
    assert len(prompts) == 2
    assert "Ta réponse précédente a été refusée" in prompts[1]
    assert "paragraphe remplace" in prompts[1]
    assert "ancien paragraphe" not in prompts[1]


async def test_applied_editions_are_logged_with_role_and_files(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    journal: list[tuple[str, dict[str, object]]] = []

    class _Logger:
        def info(self, msg: str, extra: dict[str, object]) -> None:
            journal.append((msg, extra))

        def warning(self, msg: str, extra: dict[str, object]) -> None:
            return None

    monkeypatch.setattr(module, "_logger", _Logger())
    service, _, _ = _preparer(tmp_path, {
        "doc-technique": [_edition("ancien paragraphe", "paragraphe remplace")],
    })

    await service.mettre_a_jour(tmp_path)

    (message, extra), = journal
    assert message == "editions_appliquees"
    assert extra["role"] == "doc-technique"
    assert any(GUIDE in str(f).replace("\\", "/") for f in extra["fichiers"])  # type: ignore[attr-defined]
