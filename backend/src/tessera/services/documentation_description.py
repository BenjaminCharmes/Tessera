"""La description du projet, écrite par le service et non par l'agent — ticket-724.

La description affichée dans Tessera vient de la clé `description` d'`agents.json`.
Aucun agent n'écrit ce fichier (ADR-027) : doc-technique **propose** un texte dans
sa sortie, et c'est le service qui le remplace, **cette clé seule**. Le reste du
fichier reste octet pour octet : un `json.dumps` du document entier le
reformaterait, et un diff de configuration noierait la ligne qui a changé.

Le texte passe par la règle « preuve » d'ADR-057, comme toute édition : il cite
le code livré qui le fonde, et ses jetons vérifiables doivent y figurer.
"""
import json
from pathlib import Path

from tessera.services.documentation_base import EditionRefusee
from tessera.services.documentation_code import MatiereCode
from tessera.services.documentation_preuve import ControleDePreuve
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Une ou deux phrases : ce que le produit fait, pas son histoire.
LONGUEUR_MAX = 220

_CLE = "description"
_BLANCS = " \t\r\n"

#: (clé, début de la clé, début de la valeur, fin de la valeur).
_Membre = tuple[str, int, int, int]


def _texte_valide(description: object) -> tuple[str, object]:
    """Le texte et la preuve d'une proposition, ou `EditionRefusee`."""
    if not isinstance(description, dict):
        raise EditionRefusee("la description attend {texte, preuve}.")
    texte = description.get("texte")
    if not isinstance(texte, str) or not texte.strip():
        raise EditionRefusee("la description est vide.")
    if "\n" in texte or "\r" in texte:
        raise EditionRefusee("la description tient sur une seule ligne.")
    if len(texte) > LONGUEUR_MAX:
        raise EditionRefusee(
            f"la description fait {len(texte)} caractères, au plus {LONGUEUR_MAX}."
        )
    return texte.strip(), description.get("preuve")


def _sauter_blancs(src: str, i: int) -> int:
    while src[i] in _BLANCS:
        i += 1
    return i


def _fin_de_chaine(src: str, debut: int) -> int:
    """Index juste après le guillemet fermant de la chaîne ouverte en `debut`."""
    i = debut + 1
    while src[i] != '"':
        i += 2 if src[i] == "\\" else 1
    return i + 1


def _fin_de_valeur(src: str, debut: int) -> int:
    """Index juste après la valeur JSON qui commence en `debut`."""
    if src[debut] == '"':
        return _fin_de_chaine(src, debut)
    profondeur = 0
    i = debut
    while True:
        c = src[i]
        if c == '"':
            i = _fin_de_chaine(src, i)
            continue
        if c in "{[":
            profondeur += 1
        elif c in "}]" and profondeur == 0:
            break
        elif c in "}]":
            profondeur -= 1
        elif c == "," and profondeur == 0:
            break
        i += 1
    return len(src[:i].rstrip())


def _membres(src: str) -> list[_Membre]:
    """Les membres du premier niveau, sans toucher à ce qui est imbriqué.

    Le document a déjà été lu par `json.loads` : sa structure est valide, seuls
    des blancs séparent les jetons.
    """
    i = src.index("{") + 1
    membres: list[_Membre] = []
    while True:
        i = _sauter_blancs(src, i)
        if src[i] == "}":
            return membres
        if src[i] == ",":
            i += 1
            continue
        debut_cle = i
        i = _fin_de_chaine(src, i)
        cle = str(json.loads(src[debut_cle:i]))
        i = _sauter_blancs(src, _sauter_blancs(src, i) + 1)
        fin = _fin_de_valeur(src, i)
        membres.append((cle, debut_cle, i, fin))
        i = fin


def _inserer(src: str, membres: list[_Membre], valeur: str) -> str:
    """Ajoute la clé après le dernier membre, avec la mise en forme du fichier."""
    membre = f'"{_CLE}": {valeur}'
    if not membres:
        fin = src.rindex("}")
        eol = "\r\n" if "\r\n" in src else "\n"
        return f"{src[:fin].rstrip()}{eol}  {membre}{eol}{src[fin:]}"
    _, debut_cle, _, fin = membres[-1]
    avant = src[:debut_cle]
    separation = avant[len(avant.rstrip()) :]
    return f"{src[:fin]},{separation}{membre}{src[fin:]}"


def remplacer_description(src: str, texte: str) -> str:
    """Le document avec sa clé `description` du premier niveau remplacée ou ajoutée."""
    valeur = json.dumps(texte, ensure_ascii=False)
    membres = _membres(src)
    existants = [m for m in membres if m[0] == _CLE]
    if not existants:
        return _inserer(src, membres, valeur)
    _, _, debut, fin = existants[-1]
    return src[:debut] + valeur + src[fin:]


def ecrire_description(
    manifeste: Path, description: object, controle: ControleDePreuve
) -> bool:
    """Écrit la description dans `manifeste` ; rend False si elle y était déjà.

    Lève `EditionRefusee` avant toute écriture : texte vide, multiligne ou trop
    long, preuve absente ou fausse, fichier illisible ou qui n'est pas un objet.
    """
    texte, preuve = _texte_valide(description)
    controle.verifier({"nouveau": texte, "preuve": preuve}, "agents.json")
    if not manifeste.is_file():
        raise EditionRefusee("agents.json est introuvable.")
    src = manifeste.read_bytes().decode("utf-8")
    try:
        valide = isinstance(json.loads(src.lstrip("﻿")), dict)
    except json.JSONDecodeError:
        valide = False
    if not valide:
        raise EditionRefusee("agents.json n'est pas un objet JSON lisible.")
    nouveau = remplacer_description(src, texte)
    if nouveau == src:
        return False
    manifeste.write_bytes(nouveau.encode("utf-8"))
    return True


def appliquer_description(
    manifeste: Path | None,
    donnees: dict[str, object],
    matiere: MatiereCode,
    tickets: str,
    role: str,
) -> tuple[list[str], list[str]]:
    """Traite la `description` d'une réponse : (fichiers écrits, refus).

    `matiere` et `tickets` sont ce que l'agent a lu, contre quoi se contrôle la
    preuve. Un refus se journalise et se rend ; il n'arrête pas le reste du lot.
    """
    if manifeste is None or _CLE not in donnees:
        return [], []
    try:
        ecrit = ecrire_description(
            manifeste, donnees[_CLE], ControleDePreuve(matiere, tickets)
        )
    except EditionRefusee as exc:
        _logger.warning("description_refusee", extra={"role": role, "motif": str(exc)})
        return [], [f"{role} : description refusée — {exc}"]
    return ([str(manifeste)] if ecrit else []), []
