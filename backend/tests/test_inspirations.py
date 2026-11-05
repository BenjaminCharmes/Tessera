"""The inspirations register only cites files that exist — ticket-790.

`docs/inspirations.md` says which Tessera files derive from an external tool.
A cited path that has moved or been deleted would make the register lie about
what to re-read when the tool evolves.
"""
import re
from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]
_REGISTRE = _RACINE / "docs" / "inspirations.md"

_CHAMPS = ("Dépôt", "Version reprise", "Date de reprise", "Mode", "Licence")
_MODES = ("`idées réécrites`", "`copie épinglée`")


def _sections(texte: str) -> dict[str, str]:
    """Split the register into one block per tool (`## Name`)."""
    blocs = re.split(r"^## ", texte, flags=re.MULTILINE)[1:]
    return {b.splitlines()[0].strip(): b for b in blocs}


def _ligne(bloc: str, champ: str) -> str:
    """Return the value cell of the `| champ | valeur |` row, or an empty string."""
    m = re.search(rf"^\|\s*{re.escape(champ)}\s*\|(.*)\|\s*$", bloc, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


def fichiers_derives(bloc: str) -> list[str]:
    """Paths cited in the `Fichiers dérivés` row of a tool's block."""
    return re.findall(r"`([^`]+)`", _ligne(bloc, "Fichiers dérivés"))


def chemins_absents(texte: str, racine: Path) -> list[str]:
    """Derived files cited in the register that do not exist under `racine`."""
    return [
        f"{outil} : {chemin}"
        for outil, bloc in _sections(texte).items()
        for chemin in fichiers_derives(bloc)
        if not (racine / chemin).is_file()
    ]


def test_every_derived_file_cited_in_the_register_exists() -> None:
    texte = _REGISTRE.read_text(encoding="utf-8")

    assert chemins_absents(texte, _RACINE) == []


def test_register_fails_on_a_missing_derived_file(tmp_path: Path) -> None:
    (tmp_path / "present.md").write_text("x", encoding="utf-8")
    texte = (
        "## Outil\n\n| Champ | Valeur |\n| --- | --- |\n"
        "| Fichiers dérivés | `present.md`, `absent.md` |\n"
    )

    assert chemins_absents(texte, tmp_path) == ["Outil : absent.md"]


def test_register_lists_humanizer_and_impeccable_at_their_commit() -> None:
    sections = _sections(_REGISTRE.read_text(encoding="utf-8"))

    assert "blader/humanizer" in _ligne(sections["Humanizer"], "Dépôt")
    assert "0ef9fe5bc357" in _ligne(sections["Humanizer"], "Version reprise")
    assert "pbakaus/impeccable" in _ligne(sections["Impeccable"], "Dépôt")
    assert "df3a4abe7d08" in _ligne(sections["Impeccable"], "Version reprise")


def test_each_entry_has_its_fields_a_known_mode_and_a_derived_file() -> None:
    sections = _sections(_REGISTRE.read_text(encoding="utf-8"))

    assert sections, "no entry in docs/inspirations.md"
    for outil, bloc in sections.items():
        for champ in _CHAMPS:
            assert _ligne(bloc, champ), f"{outil} : champ {champ} absent"
        assert _ligne(bloc, "Mode") in _MODES, f"{outil} : mode inconnu"
        assert fichiers_derives(bloc), f"{outil} : aucun fichier dérivé"


def test_derived_files_follow_what_each_tool_inspired() -> None:
    sections = _sections(_REGISTRE.read_text(encoding="utf-8"))

    assert "agents/prompts/doc-fonctionnelle.md" in fichiers_derives(sections["Humanizer"])
    assert "agents/plugin/skills/design-ui/SKILL.md" in fichiers_derives(
        sections["Impeccable"]
    )
