"""Manage Tessera's secrets in the system vault (ADR-073, design §5).

``python -m tessera.coffre_cli migrer|set NOM|supprimer NOM|lister``, run by
``scripts/tessera.ps1 secrets``. No value is ever printed, passed as an
argument or written to a temporary file holding it: ``set`` reads the value
on standard input. This module does not import ``tessera.config``: building the
settings would read the vault, and refuse to start in the cases this command
exists to repair.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import TextIO

from dotenv import dotenv_values

from tessera.coffre import NOMS_SECRETS, Coffre, CoffreAbsent, CoffreEnErreur, coffre_du_systeme
from tessera.config_coffre import est_placeholder

# Le `.env` de Tessera, à la racine du dépôt (même ancrage que `config.py`).
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

_LIGNE_SECRET = re.compile(r"^\s*(?:export\s+)?([A-Z0-9_]+)\s*=")
_LIGNE_SOURCE = re.compile(r"^\s*(?:export\s+)?SECRETS_SOURCE\s*=", re.MULTILINE)
_MARQUE = "# {nom} : dans le coffre (tessera.ps1 secrets)"

_ROTATION = (
    "Ces valeurs ont existé en clair sur le disque : si celui-ci est sauvegardé ou "
    "synchronisé, régénère les jetons concernés. Le coffre ne rattrape pas ce passé."
)


def _ouvrir() -> Coffre | None:
    """Open the vault, or print why it cannot be and return None."""
    try:
        return coffre_du_systeme()
    except CoffreAbsent:
        message = "aucun coffre utilisable sur cette machine (SECRETS_SOURCE=env y reste possible)"
    except CoffreEnErreur:
        message = "coffre en erreur : déverrouille-le puis relance"
    print(f"secrets : {message}", file=sys.stderr)
    return None


def _fin_de_ligne(ligne: str) -> str:
    return "\r\n" if ligne.endswith("\r\n") else "\n"


def _ranger(coffre: Coffre, nom: str, valeur: str) -> str:
    """Put one value in the vault; return ``rangé``, ``déjà``, ``conflit`` or ``échec``."""
    try:
        present = coffre.lire(nom)
        if present is not None:
            return "déjà" if present == valeur else "conflit"
        coffre.ecrire(nom, valeur)  # relit et compare
    except (CoffreAbsent, CoffreEnErreur):
        return "échec"
    return "rangé"


def _ecrire_a_cote(fichier: Path, texte: str) -> None:
    """Write ``fichier`` through a sibling file and ``os.replace``, never a backup."""
    descripteur, voisin = tempfile.mkstemp(dir=fichier.parent, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(descripteur, "w", encoding="utf-8", newline="") as flux:
            flux.write(texte)
        os.replace(voisin, fichier)
    except BaseException:
        Path(voisin).unlink(missing_ok=True)
        raise


def migrer(fichier: Path) -> int:
    """Move every secret of ``fichier`` into the vault, then blank its line."""
    coffre = _ouvrir()
    if coffre is None:
        return 2
    if not fichier.is_file():
        print(f"secrets : {fichier} introuvable", file=sys.stderr)
        return 2
    valeurs = dotenv_values(fichier)
    with fichier.open(encoding="utf-8", newline="") as flux:
        lignes = flux.readlines()
    original = "".join(lignes)
    issues: dict[str, str] = {}
    for index, ligne in enumerate(lignes):
        trouve = _LIGNE_SECRET.match(ligne)
        nom = trouve.group(1) if trouve else ""
        valeur = valeurs.get(nom) or ""
        if nom not in NOMS_SECRETS or not valeur or est_placeholder(valeur):
            continue
        issue = issues.setdefault(nom, _ranger(coffre, nom, valeur))
        if issue in ("rangé", "déjà"):
            lignes[index] = _MARQUE.format(nom=nom) + _fin_de_ligne(ligne)
    texte = "".join(lignes)
    if issues and not _LIGNE_SOURCE.search(texte):
        fin = _fin_de_ligne(lignes[-1]) if lignes else "\n"
        if texte and not texte.endswith("\n"):
            texte += fin
        texte += "SECRETS_SOURCE=coffre" + fin
    if texte != original:
        _ecrire_a_cote(fichier, texte)
    return _rapporter(issues)


def _rapporter(issues: dict[str, str]) -> int:
    """Print one line per secret, by name only; non-zero if one stayed behind."""
    libelles = {
        "rangé": "rangé dans le coffre, ligne retirée de .env",
        "déjà": "déjà dans le coffre, ligne retirée de .env",
        "conflit": "le coffre porte une autre valeur : ligne gardée "
        "(tranche avec `tessera.ps1 secrets set`)",
        "échec": "écriture ou relecture du coffre en échec : ligne gardée",
    }
    for nom, issue in issues.items():
        print(f"{nom} : {libelles[issue]}")
    if not issues:
        print("Aucun secret à ranger dans .env.")
    elif any(issue == "rangé" for issue in issues.values()):
        print(_ROTATION)
    return 1 if any(i in ("conflit", "échec") for i in issues.values()) else 0


def definir(nom: str, entree: TextIO) -> int:
    """Store the value read on ``entree`` under ``nom``."""
    if nom not in NOMS_SECRETS:
        print(f"secrets : {nom} n'est pas un secret de Tessera", file=sys.stderr)
        return 2
    valeur = entree.read().rstrip("\r\n")
    if not valeur:
        print("secrets : valeur vide, rien n'est écrit", file=sys.stderr)
        return 2
    coffre = _ouvrir()
    if coffre is None:
        return 2
    try:
        coffre.ecrire(nom, valeur)
    except (CoffreAbsent, CoffreEnErreur):
        print(f"{nom} : écriture ou relecture du coffre en échec", file=sys.stderr)
        return 1
    print(f"{nom} : rangé dans le coffre")
    return 0


def supprimer(nom: str) -> int:
    """Remove ``nom`` from the vault."""
    coffre = _ouvrir()
    if coffre is None:
        return 2
    try:
        coffre.supprimer(nom)
    except (CoffreAbsent, CoffreEnErreur):
        print(f"{nom} : suppression en échec", file=sys.stderr)
        return 1
    print(f"{nom} : retiré du coffre")
    return 0


def lister(fichier: Path) -> int:
    """Print where each secret lives: ``coffre``, ``.env`` or ``absent``."""
    coffre = _ouvrir()
    try:
        presents = coffre.presents() if coffre else frozenset()
    except (CoffreAbsent, CoffreEnErreur):
        presents = frozenset()
    valeurs = dotenv_values(fichier) if fichier.is_file() else {}
    for nom in NOMS_SECRETS:
        valeur = valeurs.get(nom) or ""
        en_clair = bool(valeur) and not est_placeholder(valeur)
        print(f"{nom} : {'coffre' if nom in presents else '.env' if en_clair else 'absent'}")
    return 0


def _analyseur() -> argparse.ArgumentParser:
    commun = argparse.ArgumentParser(add_help=False)
    commun.add_argument("--env-file", type=Path, default=_ENV_FILE)
    analyseur = argparse.ArgumentParser(prog="python -m tessera.coffre_cli")
    sous = analyseur.add_subparsers(dest="commande", required=True)
    sous.add_parser("migrer", parents=[commun])
    sous.add_parser("lister", parents=[commun])
    for commande in ("set", "supprimer"):
        sous.add_parser(commande, parents=[commun]).add_argument("nom")
    return analyseur


def main(argv: list[str] | None = None, entree: TextIO | None = None) -> int:
    """Run one subcommand and return its exit code."""
    arguments = _analyseur().parse_args(argv)
    fichier: Path = arguments.env_file
    if arguments.commande == "migrer":
        return migrer(fichier)
    if arguments.commande == "set":
        return definir(arguments.nom, entree or sys.stdin)
    if arguments.commande == "supprimer":
        return supprimer(arguments.nom)
    return lister(fichier)


if __name__ == "__main__":
    sys.exit(main())
