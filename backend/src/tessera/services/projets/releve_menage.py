"""Read-only housekeeping report over the projects folder (ticket-913).

Measures what grows or ages in each project's memory: file sizes, ADRs that no
other file cites, the age of the pipeline log, and tickets asleep in
`tickets/blocked/`. No LLM; nothing is written, archived or deleted.
"""
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tessera.services.noyau.git_commande import build_command

_TITRE_ADR = re.compile(r"^##\s+(ADR-\d+)\b", re.MULTILINE)
_NUMERO_ADR = re.compile(r"ADR-\d+(?!\d)")
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_SUFFIXES = frozenset({".md", ".py", ".json", ".ts", ".tsx", ".txt", ".toml", ".yml", ".yaml"})
_DOSSIERS_IGNORES = frozenset({".git", "node_modules", ".venv", "__pycache__", "dist"})
_TAILLE_MAX_LECTURE = 2_000_000


@dataclass(frozen=True)
class FichierMemoire:
    nom: str
    caracteres: int
    lignes: int


def _lire(chemin: Path) -> str:
    """Text of a file, empty when unreadable or too large."""
    try:
        if chemin.stat().st_size > _TAILLE_MAX_LECTURE:
            return ""
        return chemin.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def fichiers_memoire(projet: Path) -> list[FichierMemoire]:
    """Files of `memory/`, biggest first (size in characters)."""
    dossier = projet / "memory"
    if not dossier.is_dir():
        return []
    mesures = []
    for chemin in dossier.rglob("*"):
        if chemin.is_file():
            texte = _lire(chemin)
            mesures.append(FichierMemoire(chemin.relative_to(dossier).as_posix(), len(texte), len(texte.splitlines())))
    return sorted(mesures, key=lambda f: (-f.caracteres, f.nom))


def _fichiers_du_projet(projet: Path) -> list[Path]:
    trouves = []
    for chemin in projet.rglob("*"):
        relatif = chemin.relative_to(projet).parts
        if chemin.is_file() and chemin.suffix in _SUFFIXES and not _DOSSIERS_IGNORES.intersection(relatif):
            trouves.append(chemin)
    return trouves


def adr_et_orphelines(projet: Path) -> tuple[list[str], list[str]]:
    """All ADR ids of `memory/decisions.md`, and those no other file cites."""
    decisions = projet / "memory" / "decisions.md"
    adrs = _TITRE_ADR.findall(_lire(decisions)) if decisions.is_file() else []
    citees: set[str] = set()
    for chemin in _fichiers_du_projet(projet):
        if chemin != decisions:
            citees.update(_NUMERO_ADR.findall(_lire(chemin)))
    return adrs, [a for a in adrs if a not in citees]


def journal(projet: Path) -> tuple[int, str | None]:
    """Line count of the pipeline log and the date of its oldest dated line."""
    chemin = projet / "memory" / "pipeline-log.md"
    if not chemin.is_file():
        return 0, None
    lignes = _lire(chemin).splitlines()
    for ligne in lignes:
        trouve = _DATE.search(ligne)
        if trouve:
            return len(lignes), trouve.group(1)
    return len(lignes), None


def _dernier_commit(projet: Path, chemin: Path) -> datetime | None:
    try:
        sortie = subprocess.run(
            build_command(("log", "-1", "--format=%cI", "--", chemin.relative_to(projet).as_posix())),
            cwd=projet, capture_output=True, text=True, timeout=30, check=False,
        ).stdout.strip()
        return datetime.fromisoformat(sortie) if sortie else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def tickets_endormis(projet: Path, age_jours: int, maintenant: datetime | None = None) -> list[tuple[str, date]]:
    """Blocked tickets whose last commit is older than `age_jours`, oldest first."""
    dossier = projet / "tickets" / "blocked"
    if not dossier.is_dir():
        return []
    limite = (maintenant or datetime.now(UTC)) - timedelta(days=age_jours)
    endormis = []
    for fiche in sorted(dossier.glob("*.md")):
        dernier = _dernier_commit(projet, fiche)
        if dernier is not None and dernier < limite:
            endormis.append((fiche.name, dernier.date()))
    return sorted(endormis, key=lambda e: (e[1], e[0]))


def _section_projet(projet: Path, age_jours: int) -> list[str]:
    sortie = [f"## {projet.name}", "", "### Memory files", ""]
    fichiers = fichiers_memoire(projet)
    sortie += [f"- `{f.nom}` — {f.caracteres} characters, {f.lignes} lines" for f in fichiers] or ["- none"]
    adrs, orphelines = adr_et_orphelines(projet)
    sortie += ["", f"### ADRs ({len(adrs)})", ""]
    sortie += [f"- {a} — cited by no other file" for a in orphelines] or ["- every ADR is cited"]
    lignes, plus_vieille = journal(projet)
    sortie += ["", "### Pipeline log", "", f"- {lignes} lines, oldest line: {plus_vieille or 'none'}"]
    sortie += ["", f"### Blocked tickets older than {age_jours} days", ""]
    endormis = tickets_endormis(projet, age_jours)
    sortie += [f"- `{nom}` — last commit {jour.isoformat()}" for nom, jour in endormis] or ["- none"]
    return sortie + [""]


def releve_menage(racine: Path, age_jours: int = 30, projets: list[str] | None = None) -> str:
    """Markdown report for each project of `racine` that carries a `CLAUDE.md`."""
    sortie = ["# Housekeeping report", ""]
    for dossier in sorted(p for p in racine.iterdir() if p.is_dir()):
        if (dossier / "CLAUDE.md").is_file() and (projets is None or dossier.name in projets):
            sortie += _section_projet(dossier, age_jours)
    return "\n".join(sortie)
