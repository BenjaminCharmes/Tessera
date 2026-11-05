"""What a project declares in prose: name, description, agents, stack — ticket-691.

Split out of `project_loader`. These functions read the text of `CLAUDE.md`
and `README.md`; they never touch `agents.json`.
"""

import re
from pathlib import Path

#: `CLAUDE.md` accolé au titre, avant ou après un tiret. Les prompts qui
#: génèrent ces fichiers écrivent « # CLAUDE.md — NomDuProjet », ce qui est un
#: bon en-tête de fichier et un mauvais nom de projet.
_DECORATION = re.compile(
    r"^\s*CLAUDE\.md\s*$"                       # le titre n'est que le fichier
    r"|^\s*CLAUDE\.md\s*[—:–-]\s*(?:projet\s+)?"  # « CLAUDE.md — projet X »
    r"|\s*[—:–-]\s*CLAUDE\.md\s*$",              # « X — CLAUDE.md »
    re.IGNORECASE,
)

#: Débuts de paragraphe qui ne sont pas de la prose : citation (une note aux
#: agents, « > Fichier local uniquement… »), séparateur, HTML, tableau, code,
#: liste.
_PAS_DE_LA_PROSE = (">", "---", "***", "<", "|", "```", "- ", "* ", "!")

#: Un paragraphe qui s'adresse aux agents (« Profil agent : … ») ne décrit pas
#: le projet.
_CONSIGNE_AUX_AGENTS = re.compile(r"^(\*\*)?profil (agent|attendu)\b", re.IGNORECASE)

_MARKDOWN_EN_LIGNE: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),  # image
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),  # lien → son texte
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),  # gras
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"\1"),  # italique
    (re.compile(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])"), r"\1"),
    (re.compile(r"`([^`]+)`"), r"\1"),  # code
)


def parse_name(content: str, fallback: str) -> str:
    """Le nom lisible du projet, tiré du premier titre du CLAUDE.md (ADR-007).

    Le titre sert deux choses à la fois : il annonce le fichier et il nomme le
    projet. Les deux ne veulent pas la même chose — la barre latérale affichait
    « Lyra — CLAUDE.md » et « CLAUDE.md — projet ide-core ». Le nom du
    fichier est retiré ici, parce que c'est ici qu'on lit un **nom de projet**
    (ticket-093).
    """
    for line in content.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if not m:
            continue
        titre = _DECORATION.sub("", m.group(1).strip()).strip()
        return titre or fallback
    return fallback


def _texte_brut(markdown: str) -> str:
    """Inline Markdown → plain text, whitespace collapsed (ticket-399 cards)."""
    texte = markdown
    for motif, remplacement in _MARKDOWN_EN_LIGNE:
        texte = motif.sub(remplacement, texte)
    return re.sub(r"\s+", " ", texte).strip()


def _introduction(content: str) -> str:
    """The first prose paragraph between the title and the first section.

    Les notes aux agents (citations), les séparateurs, le HTML d'un README de
    profil et les listes ne décrivent pas le projet : ils sont sautés.
    """
    paragraphes: list[list[str]] = [[]]
    titre_vu = False
    for ligne in content.splitlines():
        brute = ligne.strip()
        if brute.startswith("#"):
            if titre_vu or brute.startswith("##"):
                break
            titre_vu = True
            continue
        if not brute:
            paragraphes.append([])
        else:
            paragraphes[-1].append(brute)
    for lignes in paragraphes:
        if (
            lignes
            and not lignes[0].startswith(_PAS_DE_LA_PROSE)
            and not _CONSIGNE_AUX_AGENTS.match(lignes[0])
        ):
            return _texte_brut(" ".join(lignes))
    return ""


def parse_description(content: str, readme: str = "") -> str:
    """The project's description, in plain text.

    D'abord l'introduction du `CLAUDE.md` ; à défaut (un `CLAUDE.md` qui ne
    s'adresse qu'aux agents), celle du `README.md`.
    """
    return _introduction(content) or _introduction(readme)


def lire_readme(project_path: Path) -> str:
    """The project's `README.md`, or an empty string when missing or unreadable."""
    try:
        return (project_path / "README.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def parse_active_agents(content: str) -> list[str]:
    """The roles listed under the `## Agents actifs` section of `CLAUDE.md`."""
    in_section = False
    agents: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Agents actifs", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section:
            m = re.match(r"^-\s+`(\w+)`", line)
            if m:
                agents.append(m.group(1))
    return agents


def parse_stack(content: str) -> str | None:
    """The text of the `## Stack` section of `CLAUDE.md`, or None when empty."""
    in_section = False
    lines: list[str] = []
    for line in content.splitlines():
        if re.match(r"^##\s+Stack", line):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if in_section and line.strip():
            lines.append(line.strip())
    return "\n".join(lines) if lines else None
