"""The supervisor's closed action registry and its deterministic guards — ticket-851.

Pure functions: no model call, no write, no I/O (ADR-080). The model only
*chooses* a `Decision` among four actions; the code checks it here, then acts
elsewhere. Anything unreadable, off-schema or off-registry is refused, so the
supervisor does nothing (fail closed, ADR-039).
"""
import posixpath
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, get_args

RAISON_MAX = 300


class Action(StrEnum):
    """The only things the supervisor can do."""

    TRIER = "trier"
    DECIDER = "decider"
    RECONFIER_PR = "reconfier_pr"
    RELANCER_FILE = "relancer_file"


Verdict = Literal["agir", "a_toi", "rien"]


@dataclass(frozen=True)
class Decision:
    """One choice of the model: what to do, on what, and why (≤ 300 characters)."""

    action: Action
    cible: str
    verdict: Verdict
    raison: str


# Pas de `additionalProperties: false` : le tri (ticket-855) étend ce schéma.
SCHEMA_DECISION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": [action.value for action in Action]},
        "cible": {"type": "string", "minLength": 1},
        "verdict": {"type": "string", "enum": list(get_args(Verdict))},
        "raison": {"type": "string", "maxLength": RAISON_MAX},
    },
    "required": ["action", "cible", "verdict", "raison"],
}


def _action(valeur: object) -> Action:
    for action in Action:
        if valeur == action.value:
            return action
    raise ValueError(f"Action hors registre : {valeur!r}")


def _verdict(valeur: object) -> Verdict:
    if valeur == "agir":
        return "agir"
    if valeur == "a_toi":
        return "a_toi"
    if valeur == "rien":
        return "rien"
    raise ValueError(f"Verdict hors schéma : {valeur!r}")


def lire_decision(brut: object) -> Decision:
    """Read a model output as a `Decision`; `ValueError` if off-schema or off-registry."""
    if not isinstance(brut, dict):
        raise ValueError("Décision hors schéma : un objet est attendu")
    for champ in ("action", "cible", "verdict", "raison"):
        if not isinstance(brut.get(champ), str):
            raise ValueError(f"Décision hors schéma : « {champ} » doit être un texte")
    if not brut["cible"].strip():
        raise ValueError("Décision hors schéma : « cible » est vide")
    if len(brut["raison"]) > RAISON_MAX:
        raise ValueError(f"Décision hors schéma : « raison » dépasse {RAISON_MAX} caractères")
    return Decision(_action(brut["action"]), brut["cible"], _verdict(brut["verdict"]), brut["raison"])


# --- Filtre de sensibilité -------------------------------------------------

_PORTES = frozenset({27, 31, 37, 39, 53, 55, 67, 73, 80})
# « ADR-027 », « ADR 27 », mais aussi « ADR-006, 031 » : on relit chaque numéro de la liste.
_LISTE_ADR = re.compile(r"\badr[-\s]?\d+(?:\s*(?:,|/|et|and)\s*\d+)*", re.IGNORECASE)
_MOTS = (
    "secret", "jeton", "budget", "quota", "suppress", "supprim",
    "professionnel", "professional", "force", "superviseur", "supervisor",
)


def _plier(texte: str) -> str:
    """Lowercase without accents, so « Jeton » and « forcé » are read like their root."""
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c)).casefold()


def est_sensible(texte: str) -> bool:
    """Whether a rule or lesson names a door, a sensitive word, or the supervisor itself."""
    for liste in _LISTE_ADR.findall(texte):
        if any(int(numero) in _PORTES for numero in re.findall(r"\d+", liste)):
            return True
    plie = _plier(texte)
    return any(mot in plie for mot in _MOTS)


# --- Garde de chemins ------------------------------------------------------

_PERMIS: dict[Action, tuple[str, ...]] = {
    Action.TRIER: ("tickets/**",),
    Action.DECIDER: ("memory/lecons.md", "memory/contraintes.md", "memory/supervision.md"),
    Action.RECONFIER_PR: (),
    Action.RELANCER_FILE: (),
}
_FICHIERS_INTERDITS = frozenset({"agents.json", "claude.md"})
_DOSSIERS_INTERDITS = frozenset({".git", ".github"})
_SETTINGS = re.compile(r"(?:^|/)\.claude/settings")


def chemins_permis(action: Action) -> tuple[str, ...]:
    """Globs, relative to the project, that `action` may write; none for a read-only action."""
    return _PERMIS[action]


def _normaliser(chemin: str) -> str | None:
    """Slash-separated, `..` resolved, lowercase; `None` for an absolute or escaping path."""
    brut = chemin.strip().replace("\\", "/")
    if brut.startswith("/") or re.match(r"[A-Za-z]:", brut):
        return None
    net = posixpath.normpath(brut).casefold()
    if net in (".", "..") or net.startswith("../"):
        return None
    return net


def _toujours_interdit(net: str) -> bool:
    parties = net.split("/")
    return (
        bool(_DOSSIERS_INTERDITS.intersection(parties))
        or parties[-1] in _FICHIERS_INTERDITS
        or _SETTINGS.search(net) is not None
        or net == "memory/decisions.md"
    )


def _dans_les_globs(net: str, globs: tuple[str, ...]) -> bool:
    for motif in globs:
        racine = motif.casefold()
        if racine.endswith("/**"):
            if net.startswith(racine[:-2]):
                return True
        elif net == racine:
            return True
    return False


def refus_de_chemin(modifies: Iterable[str], action: Action) -> str | None:
    """The reason the first offending path is refused for `action`, or `None` if all pass."""
    globs = chemins_permis(action)
    for chemin in modifies:
        net = _normaliser(chemin)
        if net is None:
            return f"{chemin} : chemin hors du projet"
        if _toujours_interdit(net):
            return f"{chemin} : fichier que le superviseur n'écrit jamais"
        if not _dans_les_globs(net, globs):
            return f"{chemin} : hors des chemins permis à l'action {action.value}"
    return None


# --- Déplacement pur d'un bloc ---------------------------------------------

_TITRE_PROPOSEES = "proposées"


def _titre(ligne: str) -> str | None:
    """Casefolded title of a level-2 heading line, `None` for any other line."""
    if ligne.startswith("##") and not ligne.startswith("###"):
        return ligne[2:].strip().casefold()
    return None


def _sections(lignes: list[str]) -> list[str | None]:
    """For each line, the title of the level-2 section that holds it."""
    courante: str | None = None
    resultat: list[str | None] = []
    for ligne in lignes:
        courante = _titre(ligne) or courante
        resultat.append(courante)
    return resultat


def _positions(lignes: list[str], bloc: list[str], titre: str) -> list[int]:
    """Start indexes where `bloc` sits whole, and complete, inside the section `titre`."""
    sections, n = _sections(lignes), len(bloc)
    trouves: list[int] = []
    for debut in range(len(lignes) - n + 1):
        fin = debut + n
        suite = lignes[fin] if fin < len(lignes) else ""
        if (
            lignes[debut:fin] == bloc
            and all(s == titre for s in sections[debut:fin])
            and not (suite.strip() and suite[0].isspace())  # la règle continue en retrait
        ):
            trouves.append(debut)
    return trouves


def _reste(lignes: list[str], debut: int, n: int) -> list[str]:
    """The non-blank lines left once the `n` lines from `debut` are removed."""
    return [ligne for ligne in lignes[:debut] + lignes[debut + n:] if ligne.strip()]


def deplacement_pur(avant: str, apres: str, bloc: str, vers: str) -> bool:
    """Whether `apres` is `avant` with `bloc` moved from `## Proposées` to section `vers`.

    The block must be found line for line in both texts, and every other
    non-blank line must be unchanged and in place: a block edited on the way,
    or any extra line, refuses.
    """
    lignes_bloc = bloc.strip("\r\n").splitlines()
    cible = vers.strip().removeprefix("##").strip().casefold()
    if not any(ligne.strip() for ligne in lignes_bloc) or cible in ("", _TITRE_PROPOSEES):
        return False
    if any(_titre(ligne) is not None for ligne in lignes_bloc):
        return False
    if ("\r\n" in avant) != ("\r\n" in apres):
        return False
    n, l_avant, l_apres = len(lignes_bloc), avant.splitlines(), apres.splitlines()
    restes = [_reste(l_avant, i, n) for i in _positions(l_avant, lignes_bloc, _TITRE_PROPOSEES)]
    return any(
        _reste(l_apres, i, n) in restes for i in _positions(l_apres, lignes_bloc, cible)
    )
