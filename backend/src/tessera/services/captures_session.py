"""Read the access token a capture session needs — ticket-437.

Le jeton se lit côté serveur dans le `.env` du projet. Il ne sort de ce module
que pour l'entrée standard du script de capture : jamais dans une réponse, un
journal, une ligne de commande ou `agents.json`.
"""
from pathlib import Path

from tessera.services.captures_config import SessionCaptures


def _valeur(ligne: str, nom: str) -> str | None:
    ligne = ligne.strip()
    if not ligne or ligne.startswith("#"):
        return None
    ligne = ligne.removeprefix("export ").lstrip()
    cle, separateur, valeur = ligne.partition("=")
    if not separateur or cle.strip() != nom:
        return None
    valeur = valeur.strip()
    if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in "\"'":
        return valeur[1:-1]
    # Hors guillemets, un ` #` ouvre un commentaire de fin de ligne.
    return valeur.split(" #", 1)[0].strip()


def fichier_dans_le_projet(racine: Path, relatif: str) -> Path | None:
    """Resolve `relatif` under `racine`, or None when it escapes the project."""
    chemin = (racine / relatif).resolve()
    if not chemin.is_relative_to(racine.resolve()):
        return None
    return chemin


def lire_le_jeton(racine: Path, session: SessionCaptures) -> str | None:
    """Return the token named by `session`, or None when it cannot be found.

    None covers a missing file, a file outside the project, an absent
    variable and an empty value: in every case there is nothing to send.
    """
    fichier = fichier_dans_le_projet(racine, session.fichier_env)
    if fichier is None or not fichier.is_file():
        return None
    try:
        lignes = fichier.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    trouve: str | None = None
    for ligne in lignes:
        valeur = _valeur(ligne, session.jeton_env)
        if valeur is not None:
            trouve = valeur  # la dernière occurrence l'emporte, comme dotenv
    return trouve or None
