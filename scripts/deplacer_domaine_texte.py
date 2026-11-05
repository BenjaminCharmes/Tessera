"""Text rewriting behind scripts/deplacer_domaine.py (ticket-827, ADR-076).

Pure functions on a file's text: rewrite the references to moved modules,
find the ones left behind, and spot what a human must reread. Line endings are
kept as they are: every pattern stops before `\\r` or `\\n`.
"""
import ast
import re
from collections.abc import Iterable, Mapping, Set

_LONGUEUR_MAX = 100


def _alternance(noms: Iterable[str]) -> str:
    """Return a regex alternation, longest names first."""
    return "|".join(re.escape(n) for n in sorted(noms, key=len, reverse=True))


def _motif_pointe(noms: Iterable[str]) -> re.Pattern[str]:
    # `tessera.services.x` suivi d'autre chose qu'un caractère de nom :
    # `x_suite` n'est pas `x`.
    return re.compile(rf"(?<![\w.])tessera\.services\.({_alternance(noms)})(?!\w)")


def _motif_chemin(noms: Iterable[str]) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.])services/({_alternance(noms)})\.py(?!\w)")


def _motif_joint(noms: Iterable[str]) -> re.Pattern[str]:
    # `"services" / "x.py"`, la forme `Path` des chemins écrits dans les tests.
    return re.compile(rf"""(["']services["']\s*/\s*)(["'])({_alternance(noms)})\.py\2""")


def reecrire_references(texte: str, deplaces: Mapping[str, str]) -> str:
    """Rewrite dotted references and file paths to moved modules, in one pass each."""
    if not deplaces:
        return texte
    texte = _motif_pointe(deplaces).sub(
        lambda m: f"tessera.services.{deplaces[m.group(1)]}.{m.group(1)}", texte
    )
    texte = _motif_chemin(deplaces).sub(
        lambda m: f"services/{deplaces[m.group(1)]}/{m.group(1)}.py", texte
    )
    return _motif_joint(deplaces).sub(
        lambda m: f"{m.group(1)}{m.group(2)}{deplaces[m.group(3)]}{m.group(2)} / "
        f"{m.group(2)}{m.group(3)}.py{m.group(2)}",
        texte,
    )


def _rendre(indent: str, module: str, noms: list[str], commentaire: str, fin: str) -> list[str]:
    """Render one from-import, on one line when it fits, parenthesised otherwise."""
    suffixe = f"  {commentaire}" if commentaire else ""
    ligne = f"{indent}from {module} import {', '.join(noms)}{suffixe}"
    if len(ligne) <= _LONGUEUR_MAX:
        return [ligne + fin]
    corps = [f"{indent}    {nom},{fin}" for nom in noms]
    return [f"{indent}from {module} import ({suffixe}{fin}", *corps, f"{indent}){fin}"]


def _imports_du_paquet(arbre: ast.AST) -> list[ast.ImportFrom]:
    return [
        n for n in ast.walk(arbre)
        if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == "tessera.services"
    ]


def eclater_imports(texte: str, deplaces: Mapping[str, str]) -> str:
    """Split `from tessera.services import a, b` into one statement per target package."""
    try:
        arbre = ast.parse(texte)
    except SyntaxError:
        return texte
    lignes = texte.splitlines(keepends=True)
    remplacements: list[tuple[int, int, list[str]]] = []
    for noeud in _imports_du_paquet(arbre):
        if not any(a.name in deplaces for a in noeud.names) or noeud.end_lineno is None:
            continue
        debut, fin = noeud.lineno - 1, noeud.end_lineno - 1
        indent = lignes[debut][: noeud.col_offset]
        reste = lignes[fin].encode("utf-8")[noeud.end_col_offset:].decode("utf-8").strip()
        if indent.strip() or (reste and not reste.startswith("#")):
            # Instruction partagée avec une autre sur la ligne : laissée telle
            # quelle, la vérification finale la signale.
            continue
        commentaires = list(dict.fromkeys(re.findall(r"#[^\r\n]*", "".join(lignes[debut : fin + 1]))))
        commentaire = " ".join(c.strip() for c in commentaires)
        fin_de_ligne = lignes[fin][len(lignes[fin].rstrip("\r\n")):]
        groupes: dict[str, list[str]] = {}
        for alias in noeud.names:
            module = "tessera.services"
            if alias.name in deplaces:
                module = f"tessera.services.{deplaces[alias.name]}"
            nom = f"{alias.name} as {alias.asname}" if alias.asname else alias.name
            groupes.setdefault(module, []).append(nom)
        ordre = sorted(groupes, key=lambda m: m != "tessera.services")
        nouvelles = [
            ligne for m in ordre for ligne in _rendre(indent, m, groupes[m], commentaire, fin_de_ligne)
        ]
        remplacements.append((debut, fin, nouvelles))
    for debut, fin, nouvelles in sorted(remplacements, reverse=True):
        lignes[debut : fin + 1] = nouvelles
    return "".join(lignes)


def reecrire(texte: str, deplaces: Mapping[str, str], python: bool) -> str:
    """Rewrite every reference of a file: dotted paths first, then package imports."""
    texte = reecrire_references(texte, deplaces)
    return eclater_imports(texte, deplaces) if python else texte


def _numero(texte: str, position: int) -> int:
    return texte.count("\n", 0, position) + 1


def references_mortes(
    texte: str, deplaces: Mapping[str, str], modules: Mapping[str, Set[str]]
) -> list[str]:
    """List the references to an old path left in a text, as 'line: reference'.

    `modules` maps each target package to the modules it holds once moved: a
    domain named like one of its modules (`livraison`) is only alive when
    followed by one of them, or by ` import`.
    """
    if not deplaces:
        return []
    mortes: list[str] = []
    for m in re.finditer(r"(?<![\w.])tessera\.services\.(\w+)(?:\.(\w+))?", texte):
        nom, suite = m.group(1), m.group(2)
        if nom not in deplaces:
            continue
        if nom in modules:
            if suite is not None and suite in modules[nom]:
                continue
            if suite is None and re.match(r"\s+import\b", texte[m.end():]):
                continue
        mortes.append(f"{_numero(texte, m.start())}: tessera.services.{nom}")
    try:
        imports = _imports_du_paquet(ast.parse(texte))
    except SyntaxError:
        imports = []
    for noeud in imports:
        mortes += [
            f"{noeud.lineno}: from tessera.services import {a.name}"
            for a in noeud.names if a.name in deplaces
        ]
    for motif in (_motif_chemin(deplaces), _motif_joint(deplaces)):
        for m in motif.finditer(texte):
            mortes.append(f"{_numero(texte, m.start())}: {m.group(0)}")
    return sorted(set(mortes), key=lambda e: (int(e.split(":")[0]), e))


def lignes_a_relire(texte: str, motif: re.Pattern[str]) -> list[tuple[int, str]]:
    """Return (line number, stripped line) for every line matching motif."""
    return [
        (i, ligne.strip()) for i, ligne in enumerate(texte.splitlines(), start=1)
        if motif.search(ligne)
    ]


# Ce qui dépend de l'emplacement du fichier dans un module déplacé.
MOTIF_EMPLACEMENT = re.compile(r"__file__|parents\[\d+\]|^\s*from\s+\.")


def motif_nom_de_fichier(deplaces: Mapping[str, str]) -> re.Pattern[str]:
    """Match a bare `"x.py"` literal of a moved module, not one already under its domain."""
    exclus = "".join(rf"(?<!{re.escape(d)}[\"'] / )" for d in sorted(set(deplaces.values())))
    return re.compile(rf"""{exclus}["']({_alternance(deplaces)})\.py["']""")


def motif_texte(deplaces: Mapping[str, str]) -> re.Pattern[str]:
    """Match an old dotted path or file path in prose (docs, tickets)."""
    alt = _alternance(deplaces)
    return re.compile(rf"(?<![\w.])tessera\.services\.({alt})(?!\w)|(?<![\w.])services/({alt})\.py")
