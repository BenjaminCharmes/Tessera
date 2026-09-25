"""ADR-043, mesuree — ticket-162.

ADR-043 interdit toute donnee professionnelle dans ce depot, contenu **et**
metadonnees git. C'etait une consigne que rien ne verifiait, et elle a ete
enfreinte deux fois de suite : une adresse e-mail que personne ne relisait, puis
des noms de projets clients qu'une anonymisation precedente avait laisses
passer parce qu'elle cherchait des noms d'entreprises.

Ce fichier ne nomme aucun client, et c'est le point. Il verifie une **forme** :
toute adresse e-mail doit relever d'une liste blanche. Un domaine inconnu
echoue, qu'on ait pense a lui ou non — ce qui manquait aux deux fois.
"""

import re
import subprocess
from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]

#: Liste blanche, jamais liste noire : on ne devine pas le nom du prochain
#: client. Les forges publiques y sont parce que les tests de detection de
#: forge s'en servent comme valeurs d'exemple.
_DOMAINES_CONNUS = {
    "gmail.com",
    "github.com",
    "users.noreply.github.com",
    "noreply.github.com",
    "gitlab.com",
    "bitbucket.org",
    "dev.azure.com",
    "anthropic.com",
    "example.com",
    "exemple.com",
}

#: Un TLD alphabetique d'au moins deux lettres : sans ca, `coverage@v3.3` dans
#: un `uses:` de workflow se lit comme une adresse.
_EMAIL = re.compile(rb"[\w.+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})")

_EXTENSIONS_IGNOREES = (".lock", ".png", ".ico", ".svg", ".woff", ".woff2")

#: `icons/128x128@2x.png` dans `tauri.conf.json` a la forme exacte d'une
#: adresse dont le domaine serait `2x.png`. Un dernier label qui est une
#: extension de fichier n'est pas un TLD.
_EXTENSIONS_FICHIER = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico",
    "css", "js", "ts", "tsx", "json", "md", "py", "html", "txt", "yml", "yaml",
}


def _git(*args: str) -> str:
    """Rend la sortie decodee en UTF-8.

    Sans `encoding` explicite, Windows decode en cp1252 et un accent dans un
    corps de commit fait rendre `None` a `subprocess`, silencieusement.
    """
    sortie = subprocess.run(
        ["git", *args], cwd=_RACINE, capture_output=True, check=True
    ).stdout
    return sortie.decode("utf-8", errors="replace")


def _autorise(domaine: str) -> bool:
    d = domaine.lower().rstrip(".")
    if d.rsplit(".", 1)[-1] in _EXTENSIONS_FICHIER:
        return True
    return (
        d in _DOMAINES_CONNUS
        or d.endswith(".local")
        or d.startswith("exemple-")
        or d.endswith(".exemple.com")
    )


def _domaines(texte: bytes) -> set[str]:
    return {
        d.decode("utf-8", errors="replace")
        for d in _EMAIL.findall(texte)
        if not _autorise(d.decode("utf-8", errors="replace"))
    }


def test_aucune_adresse_inconnue_dans_les_fichiers_suivis() -> None:
    """Le contenu du depot ne porte que des adresses d'une liste connue."""
    coupables: list[str] = []
    for chemin in _git("ls-files", "-z").split("\0"):
        if not chemin or chemin.endswith(_EXTENSIONS_IGNOREES):
            continue
        fichier = _RACINE / chemin
        if not fichier.is_file():
            continue
        for domaine in _domaines(fichier.read_bytes()):
            coupables.append(f"{chemin} : @{domaine}")

    assert not coupables, "domaine inconnu :\n" + "\n".join(sorted(set(coupables))[:20])


def test_aucun_commit_n_est_signe_d_une_adresse_inconnue() -> None:
    """Auteur et committer, sur toute l'histoire.

    C'est par la que l'incident est arrive : le contenu etait propre, et une
    identite git globale signait chaque commit d'une adresse professionnelle.
    """
    adresses = {a for a in _git("log", "--all", "--format=%ae%n%ce").split("\n") if a}
    inconnues = {
        a for a in adresses if "@" not in a or not _autorise(a.split("@", 1)[1])
    }

    assert not inconnues, f"commits signes d'un domaine inconnu : {sorted(inconnues)}"


def test_aucun_message_de_commit_ne_porte_d_adresse_inconnue() -> None:
    """Un trailer `Co-authored-by` compte autant qu'une signature.

    Les squash-merges de GitHub en produisent un par PR : c'est la moitie des
    occurrences du premier incident, et elles ne sont dans aucun champ d'auteur.
    """
    messages = _git("log", "--all", "--format=%B")

    assert not _domaines(messages.encode("utf-8")), (
        f"messages portant un domaine inconnu : {sorted(_domaines(messages.encode('utf-8')))}"
    )
