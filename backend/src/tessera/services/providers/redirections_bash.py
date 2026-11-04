"""Les fichiers qu'une ligne de shell écrit, pour les formes simples — ticket-088.

Extrait de `perimetre.py`, qui pose le périmètre ; ici on ne fait que lire une
commande `Bash` et en rendre les cibles. `Bash` est couvert **pour les formes
simples** : `> fichier`, `>> fichier`, `tee fichier`. C'est ce qui attrape une
erreur, pas une frontière contre quelqu'un qui cherche à passer (ADR-031).

Un filet supplémentaire (ticket-326) attrape `python -c "open('CLAUDE.md','w')…"` :
un interpréteur invoqué en ligne avec le nom d'un fichier protégé et un mode
d'écriture. Même principe : ce qui ne se lit pas avec certitude passe.
"""
import re
import shlex
from pathlib import Path

#: `/dev/null`, `2>&1` : des flux, pas des fichiers du projet.
_NON_FICHIERS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


#: Les caractères que le shell sépare des mots : `>`, `>>`, `>|`, `&>`, `|`, `&&`…
_PONCTUATION = frozenset("();<>|&")

#: Un nom d'option court qui se termine par `t` : `-t`, `-rt` (`--target-directory`).
_RE_OPTION_REPERTOIRE = re.compile(r"^-[A-Za-z]*t$")

_RE_AFFECTATION = re.compile(r"^[A-Za-z_]\w*=")


def _jetons(commande: str) -> list[str] | None:
    """Découpe une ligne en mots et en opérateurs, ou `None` si elle ne se lit pas.

    `punctuation_chars` sépare `echo x>f` en trois jetons ; sans échappement,
    l'antislash d'un chemin Windows (`..\\f`) reste un caractère comme un autre.
    """
    lex = shlex.shlex(commande, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    lex.escape = ""
    try:
        return list(lex)
    except ValueError:
        # Guillemet non fermé : on ne sait pas lire cette ligne, donc on
        # n'invente pas de cible.
        return None


def _est_operateur(jeton: str) -> bool:
    return bool(jeton) and all(c in _PONCTUATION for c in jeton)


def _decouper(jetons: list[str]) -> tuple[list[str], list[list[str]]]:
    """Sépare les cibles de redirection des commandes simples (mots, sans opérateur)."""
    cibles: list[str] = []
    commandes: list[list[str]] = [[]]
    index = 0
    while index < len(jetons):
        jeton = jetons[index]
        if not _est_operateur(jeton):
            commandes[-1].append(jeton)
        elif "<" in jeton or ">" in jeton:
            # `2>&1` : le `2` est un descripteur, pas un argument.
            if commandes[-1] and commandes[-1][-1].isdigit():
                commandes[-1].pop()
            cible = jetons[index + 1] if index + 1 < len(jetons) else ""
            index += 1
            if ">" in jeton and _est_fichier(jeton, cible):
                cibles.append(cible)
        else:
            commandes.append([])
        index += 1
    return cibles, commandes


def _est_fichier(operateur: str, cible: str) -> bool:
    if not cible or cible in _NON_FICHIERS:
        return False
    # `>&2`, `>&-` : un descripteur. `&>f` et `> 1` écrivent bien un fichier.
    return not (operateur == ">&" and (cible.isdigit() or cible == "-"))


def _lire_arguments(args: list[str]) -> tuple[list[str], str | None]:
    """Les arguments positionnels, et le dossier de `-t` / `--target-directory`."""
    positionnels: list[str] = []
    dossier: str | None = None
    fin_options = False
    index = 0
    while index < len(args):
        arg = args[index]
        if fin_options or not arg.startswith("-") or arg == "-":
            positionnels.append(arg)
        elif arg == "--":
            fin_options = True
        elif arg.startswith("--target-directory="):
            dossier = arg.split("=", 1)[1]
        elif (arg == "--target-directory" or _RE_OPTION_REPERTOIRE.match(arg)) and (
            index + 1 < len(args)
        ):
            dossier = args[index + 1]
            index += 1
        index += 1
    return positionnels, dossier


def _nom_commande(jeton: str) -> str:
    return Path(jeton.replace("\\", "/")).name.lower().removesuffix(".exe")


def _cibles_de_commande(args: list[str]) -> list[str]:
    """Ce que `tee`, `cp`, `mv` et `rm` écrivent ou retirent.

    `tee` écrit chacun de ses arguments, où qu'il soit dans la commande. `cp`
    n'écrit que sa destination ; `mv` et `rm` retirent aussi leurs sources.
    """
    noms = [_nom_commande(a) for a in args]
    if "tee" in noms:
        return _lire_arguments(args[noms.index("tee") + 1 :])[0]
    debut = 0
    while debut < len(args) and _RE_AFFECTATION.match(args[debut]):
        debut += 1
    if debut == len(args):
        return []
    positionnels, dossier = _lire_arguments(args[debut + 1 :])
    nom = noms[debut]
    if nom == "rm":
        return positionnels
    if nom == "mv":
        return positionnels + ([dossier] if dossier else [])
    if nom == "cp":
        return [dossier] if dossier else positionnels[-1:]
    return []


def cibles_ecrites(commande: str) -> list[str]:
    """Les fichiers qu'une ligne de shell écrit, pour les formes simples.

    `>`, `>>`, `>|`, `&>`, `N>` (collés ou non), chaque argument de `tee`, et
    les destinations de `cp`, `mv` et `rm`. La ligne est **tokenisée**, jamais
    découpée à la main : `grep -r 'x > y' src/` ne redirige rien, et une
    comparaison de caractères le prendrait pour une écriture — un faux refus
    qui priverait l'agent d'une commande parfaitement légitime.

    Volontairement incomplet : ce qui ne se lit pas avec certitude n'est pas
    rendu, et passera donc.
    """
    jetons = _jetons(commande)
    if jetons is None:
        return []
    cibles, commandes = _decouper(jetons)
    for args in commandes:
        cibles.extend(_cibles_de_commande(args))
    return [c for c in cibles if c not in _NON_FICHIERS]


#: Noms et préfixes de fichiers protégés qu'on cherche dans le code inline.
_NOMS_PROTEGES_INLINE: tuple[str, ...] = (
    "CLAUDE.md",
    "CLAUDE.local.md",
    "agents.json",
    ".claude/",
    ".github/workflows/",
    ".git/",
)

#: Les motifs d'écriture d'un code inline : `open` en mode positionnel ou nommé
#: (`mode='w'`), `.write(`, `shutil`/`os` qui copient ou déplacent, et les
#: écritures de `fs` côté Node (`writeFileSync`, `createWriteStream`…).
_MOTIFS_ECRITURE: tuple[re.Pattern[str], ...] = (
    re.compile(r"""open\s*\([^)]*['"]\s*,\s*['"][wax]"""),
    re.compile(r"""open\s*\([^)]*\bmode\s*=\s*['"][wax]"""),
    re.compile(r"""\.write(?:_text|_bytes)?\s*\("""),
    re.compile(r"""\b(?:shutil|os)\s*\.\s*(?:copy2?|copyfile|copytree|move|rename|replace)\s*\("""),
    re.compile(r"""\b(?:write|append)File(?:Sync)?\s*\(|\bcreateWriteStream\s*\("""),
    re.compile(r"""\.\s*(?:copyFile|cp|rename|truncate)(?:Sync)?\s*\("""),
)

#: Interpréteurs reconnus comme premier jeton, et l'option qui porte leur code :
#: `python -c`, `node -e` (`node -c` ne fait que vérifier la syntaxe).
_OPTIONS_CODE: tuple[tuple[re.Pattern[str], frozenset[str]], ...] = (
    (re.compile(r"^python3?(\.\d+)?(\.exe)?$", re.IGNORECASE), frozenset({"-c"})),
    (
        re.compile(r"^node(\.exe)?$", re.IGNORECASE),
        frozenset({"-e", "--eval", "-p", "--print", "-pe"}),
    ),
)


def _code_inline(jetons: list[str]) -> str | None:
    """Le code que l'interpréteur du premier jeton reçoit en ligne, s'il y en a un."""
    nom = Path(jetons[0].replace("\\", "/")).name
    for motif, options in _OPTIONS_CODE:
        if motif.match(nom):
            for i, jeton in enumerate(jetons[1:-1], start=1):
                if jeton in options:
                    return jetons[i + 1]
    return None


def cibles_interpreteur_ecriture(commande: str) -> list[str]:
    """Noms protégés qu'un `python -c` ou `node -e` tente d'écrire.

    Attrape le cas `python -c "open('CLAUDE.md','w').write(…)"`, le mode nommé,
    `shutil.copy` et `writeFileSync`.
    ADR-031 : filet, pas une garantie — ce qui ne se lit pas avec certitude passe.
    """
    try:
        jetons = shlex.split(commande, posix=True)
    except ValueError:
        return []
    code = _code_inline(jetons) if jetons else None
    if code is None or not any(m.search(code) for m in _MOTIFS_ECRITURE):
        return []
    return [nom for nom in _NOMS_PROTEGES_INLINE if nom in code]


__all__ = ["cibles_ecrites", "cibles_interpreteur_ecriture"]
