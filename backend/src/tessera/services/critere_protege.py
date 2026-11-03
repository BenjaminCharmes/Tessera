"""Un critère qui exige d'écrire un fichier protégé — ticket-476.

make-your-call, ticket-017 : le dernier critère exigeait de modifier
`CLAUDE.md`, que le garde-fou refuse aux agents. Trois tours perdus, parce que
le reviewer et le validateur redemandaient ce que le pipeline ne laisse jamais
faire. Ce module repère ce critère avant le premier tour.

**La règle.** Un critère est retenu quand, dans une même proposition, il cite
entre backticks, sans espace, un chemin que `motif_de_protection` déclare
protégé (la liste vit à un seul endroit, `chemins_proteges.py`) **et** que ce
chemin est l'objet de l'écriture :

- à l'avant, 5 mots au plus, un verbe à l'infinitif, un participe ou un nom
  d'action : « Modifier `CLAUDE.md` », « Ajout d'une section dans
  `CLAUDE.md` », « section ajoutée à `CLAUDE.md` » ;
- à l'après, 3 mots au plus, le fichier est le sujet : « `CLAUDE.md` contient
  la section », « `agents.json` déclare le service », « `x/SKILL.md` créé ».
  Un « et », « puis », « pour »… en tête rompt le lien, et « généré » aussi :
  « le `CLAUDE.md` généré contient… » décrit une sortie du code livré.

Un verbe conjugué *avant* le chemin n'est pas retenu : « le service crée
`CLAUDE.md` » décrit ce que le code livré fait, pas un fichier que le run doit
écrire (l'analyseur de projet, le gabarit de `CLAUDE.md`).

**Ce qui écarte un critère**, même avec un verbe d'écriture :

- une négation dans la fenêtre (« ne », « pas », « sans », « jamais ») ;
- un mot de lecture ou de condition juste avant le chemin (« d'après »,
  « selon », « lit », « voir », « dont », « si », « quand ») ;
- le mot « test » ou « vérifie » plus haut dans la proposition : un critère
  « Un test vérifie que… » a un test pour livrable, le fichier cité n'est
  que la donnée ;
- un chemin placé entre guillemets : c'est une citation, pas une demande ;
- un jeton `chemin:12`, qui désigne une ligne lue.

C'est une heuristique, et elle choisit son erreur : un critère ambigu passe,
parce qu'un faux positif arrête un ticket valide alors qu'un faux négatif ne
coûte que ce qu'il coûtait déjà. Un chemin comme `.claude/` seul n'est pas
protégé par la liste, donc pas retenu ici.
"""
import re
from pathlib import Path

from tessera.services.providers.chemins_proteges import motif_de_protection

#: Un jeton entre backticks, sans espace.
_JETON = re.compile(r"`([^`\s]+)`")
#: Tout ce qui est entre backticks, espaces compris : masqué avant de découper
#: la phrase, pour que le point de `CLAUDE.md` n'en soit pas la fin.
_ENTRE_BACKTICKS = re.compile(r"`[^`]*`")
#: Une fin de proposition. Le point doit être suivi d'un blanc ou de la fin.
_FIN_PROPOSITION = re.compile(r"[.;!?](?=\s|$)|\n")
_FIN_APRES = re.compile(r"[.;!?](?=\s|$)|\n|,")
#: Un numéro de ligne (`src/app.py:12`) désigne une lecture, jamais un livrable.
_AVEC_LIGNE = re.compile(r":\d+$")

_MOTS_AVANT = 5
_MOTS_APRES = 3

#: Les formes qui peuvent précéder le chemin : jamais un verbe conjugué.
_FORME_AVANT = (
    r"modifier|modifié\w*|modification|mettre|mis|mise|ajouter|ajouté\w*|ajout"
    r"|créer|créé\w*|création|supprimer|supprimé\w*|suppression|écrire|éditer"
    r"|édité\w*|réécrire|réécrit\w*|remplacer|remplacé\w*|renommer|renommé\w*"
    r"|compléter|complété\w*|déclarer|déclaré\w*"
    r"|add|update|create|delete|remove|write|edit|modify"
)
#: Le chemin est le sujet : un verbe descriptif conjugué suffit.
_FORME_APRES = (
    _FORME_AVANT
    + r"|contien\w*|contenir|déclar\w*|figur\w*|mentionn\w*|décri\w*"
    + r"|contain\w*|declar\w*|mention\w*"
)
# « créé par `POST /projects` » nomme l'auteur du fichier, pas une consigne.
_VERBE_AVANT = re.compile(
    rf"(?<!\w)({_FORME_AVANT})(?!\w)(?!\s+par(?!\w))", re.IGNORECASE
)
_VERBE_APRES = re.compile(rf"(?<!\w)({_FORME_APRES})(?!\w)", re.IGNORECASE)
_NEGATION = re.compile(
    r"(?<!\w)n['’]|(?<!\w)(ne|pas|jamais|sans|aucun\w*|not|never|without)(?!\w)",
    re.IGNORECASE,
)
_MOT_DE_LECTURE = re.compile(
    r"^(d['’]après|d['’]apres|selon|lit|lire|lu|voir|cf|comme|conformément"
    r"|dont|si|quand|lorsque|où)$",
    re.IGNORECASE,
)
#: Un critère qui décrit un test ne demande pas d'écrire le fichier qu'il cite.
_MOT_DE_TEST = re.compile(
    r"(?<!\w)(tests?|teste\w*|vérifi\w*|verifi\w*|assert\w*|specs?)(?!\w)",
    re.IGNORECASE,
)
#: Ces mots, juste après le chemin, rattachent le verbe à un autre sujet.
_LIAISON = frozenset(
    {"et", "ou", "puis", "qui", "pour", "afin", "avec", "sans", "mais", "ainsi",
     "alors", "and", "or", "then", "to",
     # Un fichier que le code livré produit, pas un que le run écrit.
     "généré", "générée", "générés", "générées", "produit", "obtenu"}
)


def _mots(texte: str) -> list[str]:
    """The words of `texte`, stripped of surrounding punctuation."""
    mots = (m.strip(".,;:()«»\"“”") for m in texte.split())
    return [m for m in mots if m]


def _entre_guillemets(texte: str, position: int) -> bool:
    """True when `position` falls inside « … », “ … ” or " … "."""
    avant = texte[:position]
    if avant.count("«") > avant.count("»") or avant.count("“") > avant.count("”"):
        return True
    return avant.count('"') % 2 == 1


def _contexte(masque: str, debut: int, fin: int) -> tuple[list[str], list[str]]:
    """The words before and after the span [debut, fin) inside its clause."""
    precedent = list(_FIN_PROPOSITION.finditer(masque, 0, debut))
    depart = precedent[-1].end() if precedent else 0
    suivant = _FIN_APRES.search(masque, fin)
    arret = suivant.start() if suivant else len(masque)
    return _mots(masque[depart:debut]), _mots(masque[fin:arret])[:_MOTS_APRES]


def _ecrit_le_chemin(avant: list[str], apres: list[str]) -> bool:
    """True when the words around a path say it is written, not read or cited."""
    if any(_MOT_DE_LECTURE.match(m) for m in avant[-2:]):
        return False
    if _MOT_DE_TEST.search(" ".join(avant)):
        return False
    proches = avant[-_MOTS_AVANT:]
    if _NEGATION.search(" ".join(proches + apres)):
        return False
    if _VERBE_AVANT.search(" ".join(proches)):
        return True
    if apres and apres[0].lower() in _LIAISON:
        return False
    return _VERBE_APRES.search(" ".join(apres)) is not None


def critere_demande_ecriture(
    critere: str, project_path: Path, racine: Path
) -> str | None:
    """The protected path `critere` asks to write, or None."""
    masque = _ENTRE_BACKTICKS.sub(lambda m: "\x00" * len(m.group(0)), critere)
    for trouve in _JETON.finditer(critere):
        jeton = trouve.group(1)
        if _AVEC_LIGNE.search(jeton) or _entre_guillemets(critere, trouve.start()):
            continue
        if motif_de_protection(jeton, project_path, racine) is None:
            continue
        avant, apres = _contexte(masque, trouve.start(), trouve.end())
        if _ecrit_le_chemin(avant, apres):
            return jeton
    return None


def criteres_sur_chemins_proteges(
    criteres: list[str], project_path: Path, racine: Path
) -> list[tuple[int, str]]:
    """The criteria (1-based index, path) that ask to write a protected path."""
    retenus: list[tuple[int, str]] = []
    for numero, critere in enumerate(criteres, start=1):
        chemin = critere_demande_ecriture(critere, project_path, racine)
        if chemin is not None:
            retenus.append((numero, chemin))
    return retenus
