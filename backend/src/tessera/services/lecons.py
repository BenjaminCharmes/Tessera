"""Les leçons d'un projet — `memory/lecons.md` (ADR-074, ticket-801).

Deux sections, sur le modèle de `contraintes.md` (ADR-055) : `## Proposées`,
écrite par le service et jamais injectée ; `## En vigueur`, où un humain
déplace une leçon, seule section que lisent le codeur et le reviewer.
Une ligne est une leçon : `- Quand <situation>, <action>. (source : …)`.

Le contrôle de `refus_de_lecon` est lexical : il attrape une erreur, pas une
évasion. La relecture humaine de `## Proposées` est la seconde barrière.
"""
import re
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

from tessera.services.config_tests_touchee import NOMS_SIGNALES
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

PLAFOND_LECONS = 25  # leçons « En vigueur »
PLAFOND_OCTETS = 4096  # taille du fichier entier
LONGUEUR_MAX = 200  # caractères, source exclue

#: Le titre sous lequel les leçons entrent dans le contexte d'un agent (ticket-802).
TITRE_SECTION_LECONS = "## Leçons du projet"
ENTETE_SECTION_LECONS = (
    "Pièges observés sur ce projet. Une contrainte ou un ADR qui les contredit prévaut."
)

_FICHIER = "lecons.md"
_TITRE_PROPOSEES = "## Proposées"
_TITRE_EN_VIGUEUR = "## En vigueur"
_ENTETE = (
    "# Leçons du projet\n\n"
    "Pièges observés sur ce projet, une ligne chacun. Le service écrit sous "
    "`## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour "
    "qu'elle atteigne le codeur et le reviewer.\n\n"
)
_SOURCE = re.compile(r"\s*\(source\s*:[^)]*\)\s*$")
_MOTS = re.compile(r"\w+", re.UNICODE)
_SEUIL_DOUBLON = 0.7
_PREUVE_MIN = 20

#: Fichiers de configuration des tests (ADR-072), plus ceux de leurs scripts.
_FICHIERS_NOMMES = (*NOMS_SIGNALES, "pyproject.toml", "package.json")

#: Jetons qui désactivent une vérification, refusés seuls.
_JETONS_SEULS = ("--no-verify", "continue-on-error", "noqa", "type: ignore", "xfail")
#: Verbes (par radical) qui, joints à un test, au lint, au typage ou à la CI,
#: affaiblissent la vérification.
_VERBES = ("skip", "ignor", "désactiv", "supprim", "baiss")
_CIBLES = (
    "test", "lint", "typage", "mypy", "ruff", "eslint", "tsc", "pytest",
    "vitest", "ci", "vérification",
)


@dataclass(frozen=True)
class Lecons:
    """The lessons of a project, split by section."""

    en_vigueur: tuple[str, ...]
    proposees: tuple[str, ...]


def lire_lecons(memory_dir: Path) -> Lecons:
    """Read `lecons.md`; an absent or unreadable file gives two empty tuples."""
    try:
        contenu = (memory_dir / _FICHIER).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Lecons(en_vigueur=(), proposees=())
    sections: dict[str, list[str]] = {_TITRE_PROPOSEES: [], _TITRE_EN_VIGUEUR: []}
    courante: str | None = None
    for ligne in contenu.splitlines():
        brut = ligne.strip()
        if brut.startswith("## "):
            courante = next((t for t in sections if t.casefold() == brut.casefold()), None)
        elif courante is not None and brut.startswith("- ") and brut[2:].strip():
            sections[courante].append(brut[2:].strip())
    return Lecons(
        en_vigueur=tuple(sections[_TITRE_EN_VIGUEUR]),
        proposees=tuple(sections[_TITRE_PROPOSEES]),
    )


def section_lecons(memory_dir: Path) -> str:
    """The `## Leçons du projet` section of an agent's context, empty without lessons.

    Seules les leçons `## En vigueur` y entrent. Au-delà de `PLAFOND_OCTETS`,
    on garde celles qui tiennent et on journalise : la lecture ne lève pas.
    """
    retenues: list[str] = []
    taille = 0
    en_vigueur = lire_lecons(memory_dir).en_vigueur
    for lecon in en_vigueur:
        taille += len(lecon.encode("utf-8")) + 3
        if taille > PLAFOND_OCTETS:
            _logger.warning(
                "lecons_tronquees", extra={"retenues": len(retenues), "total": len(en_vigueur)}
            )
            break
        retenues.append(lecon)
    if not retenues:
        return ""
    corps = "\n".join(f"- {lecon}" for lecon in retenues)
    return f"{TITRE_SECTION_LECONS}\n{ENTETE_SECTION_LECONS}\n{corps}"


def nombre_proposees(memory_dir: Path) -> int:
    """How many lessons wait under `## Proposées`; 0 without a readable file."""
    return len(lire_lecons(memory_dir).proposees)


def refus_de_lecon(texte: str, preuve: str, existantes: Lecons, retour: str) -> str | None:
    """Why `texte` is refused as a lesson, or None when it is acceptable.

    `preuve` is a passage the model copies from `retour` (the run's review
    feedback); it is checked here and never stored.
    """
    texte = texte.strip()
    for controle in (_forme, _longueur):
        raison = controle(texte)
        if raison:
            return raison
    if len(preuve.strip()) < _PREUVE_MIN or preuve.strip() not in retour:
        return "preuve absente du retour du run"
    if _est_doublon(texte, existantes):
        return "doublon d'une leçon existante"
    return _verification_affaiblie(texte)


def ajouter_proposee(memory_dir: Path, texte: str, ticket_id: str, jour: date) -> bool:
    """Append a proposed lesson with its source; False when a ceiling is reached.

    Crée le fichier s'il manque. Un fichier plein se compacte à la main,
    jamais par un agent : on n'écrit alors rien.
    """
    texte = texte.strip()
    if "\n" in texte or "\r" in texte:
        raise ValueError("a lesson is a single line")
    chemin = memory_dir / _FICHIER
    try:
        contenu = chemin.read_text(encoding="utf-8")
    except FileNotFoundError:
        contenu = f"{_ENTETE}{_TITRE_PROPOSEES}\n\n{_TITRE_EN_VIGUEUR}\n"
    if len(lire_lecons(memory_dir).en_vigueur) >= PLAFOND_LECONS:
        return False
    ligne = f"- {texte} (source : {ticket_id}, {jour.isoformat()})"
    nouveau = _inserer(contenu, ligne)
    if len(nouveau.encode("utf-8")) >= PLAFOND_OCTETS:
        return False
    memory_dir.mkdir(parents=True, exist_ok=True)
    chemin.write_text(nouveau, encoding="utf-8", newline="\n")
    return True


def _inserer(contenu: str, ligne: str) -> str:
    """Place `ligne` at the end of `## Proposées`, creating the section if absent."""
    lignes = contenu.splitlines()
    debut = next(
        (i for i, t in enumerate(lignes) if t.strip().casefold() == _TITRE_PROPOSEES.casefold()),
        None,
    )
    if debut is None:
        return contenu.rstrip("\n") + f"\n\n{_TITRE_PROPOSEES}\n{ligne}\n"
    fin = next(
        (i for i in range(debut + 1, len(lignes)) if lignes[i].lstrip().startswith("## ")),
        len(lignes),
    )
    while fin > debut + 1 and not lignes[fin - 1].strip():
        fin -= 1
    lignes.insert(fin, ligne)
    # Une ligne vide sépare la section de la suivante.
    if fin + 1 < len(lignes) and lignes[fin + 1].lstrip().startswith("## "):
        lignes.insert(fin + 1, "")
    return "\n".join(lignes) + "\n"


def _forme(texte: str) -> str | None:
    if "\n" in texte or "\r" in texte or "```" in texte or "##" in texte:
        return "forme : une seule ligne, sans bloc de code ni titre"
    if not texte.startswith("Quand ") or "," not in texte:
        return "forme : « Quand <situation>, <action>. » attendu"
    return None


def _longueur(texte: str) -> str | None:
    if len(_SOURCE.sub("", texte)) > LONGUEUR_MAX:
        return f"plus de {LONGUEUR_MAX} caractères"
    return None


def _mots(texte: str) -> set[str]:
    return set(_MOTS.findall(_SOURCE.sub("", texte).casefold()))


def _est_doublon(texte: str, existantes: Lecons) -> bool:
    nouveaux = _mots(texte)
    for autre in (*existantes.en_vigueur, *existantes.proposees):
        anciens = _mots(autre)
        plus_petit = min(len(nouveaux), len(anciens))
        if plus_petit and len(nouveaux & anciens) / plus_petit >= _SEUIL_DOUBLON:
            return True
    return False


def _verification_affaiblie(texte: str) -> str | None:
    bas = texte.casefold()
    for jeton in re.findall(r"[^\s`'\"(),;]+", texte):
        base = jeton.rstrip(".").rsplit("/", 1)[-1]
        if any(fnmatch(base, motif) for motif in _FICHIERS_NOMMES):
            return f"configuration des tests nommée ({base})"
    if ".github/workflows" in bas:
        return "configuration des tests nommée (.github/workflows)"
    if any(jeton in bas for jeton in _JETONS_SEULS):
        return "vérification affaiblie : désactivation d'un contrôle"
    mots = _MOTS.findall(bas)
    verbe = any(m.startswith(v) for m in mots for v in _VERBES)
    cible = any(m.startswith(c) if len(c) > 3 else m == c for m in mots for c in _CIBLES)
    if verbe and cible:
        return "vérification affaiblie : un contrôle retiré ou ignoré"
    return None
