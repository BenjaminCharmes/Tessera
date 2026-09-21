"""Un agent n'écrit que dans son projet — ticket-085.

`cwd` place l'agent dans le dossier du projet, mais ne l'y enferme pas : rien
n'empêchait un `Write` vers `../autre-client/src/app.py`, ou vers `backend/`.
Six dépôts clients voisins dans `projects/`, et un codeur qui se trompe de
dossier écrit dans le dépôt de quelqu'un d'autre.

Même forme qu'ADR-027 pour le git : un hook `PreToolUse`, parce qu'une entrée
d'`allowed_tools` couvrant `Write` l'auto-approuve *avant* tout callback de
permission — un garde posé là serait inerte. Et un refus au niveau du SDK
produit un fait, là où une consigne de prompt ne décrit qu'une intention.

**Lire hors du projet reste permis.** Comprendre ce qui existe fait partie du
travail, et lire ne laisse rien dans le dépôt de personne.

`Bash` est couvert **pour les formes simples** : `> fichier`, `>> fichier`,
`tee fichier`. C'est ce qui attrape une erreur — un agent qui se trompe de
projet — et ce n'est pas une frontière contre quelqu'un qui cherche à passer :
`python -c "open('../x','w')"` passe, et le prétendre reviendrait à mentir sur
ce que ce module garantit. Ce qui ne se lit pas avec certitude passe, plutôt
que de refuser une commande légitime : un faux refus coûte à l'agent son moyen
de vérifier son travail.
"""
import json
import shlex
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Les outils qui laissent une trace sur le disque.
_OUTILS_QUI_ECRIVENT = frozenset({"Write", "Edit", "NotebookEdit"})

#: Ce que l'agent lit quand on lui refuse le chemin. Il doit comprendre que le
#: refus porte sur *l'endroit*, pas sur son travail — sinon il abandonne le
#: ticket au lieu de réécrire au bon endroit.
ECRITURE_REFUS = (
    "Écriture refusée : ce chemin est hors du projet sur lequel tu travailles. "
    "Écris sous la racine du projet. Si la modification concerne vraiment un "
    "autre dépôt, dis-le dans ton rapport plutôt que de l'écrire : c'est une "
    "décision qui revient à l'utilisateur."
)


def racine_autorisee(project_path: Path) -> Path:
    """Le dossier sous lequel ce projet a le droit d'écrire.

    Son propre dossier, sauf s'il déclare `git_root: ancestor` — auquel cas le
    dépôt qui le contient, parce que le projet bootstrap construit l'IDE et
    écrit donc volontairement au-dessus de lui, dans `backend/` et `frontend/`
    (ADR-028). Le dépôt, et non le simple parent : `projects/` ne serait ni la
    bonne racine ni une racine qui veut dire quelque chose.

    Seule cette valeur exacte élargit le périmètre : une valeur inconnue ou un
    fichier illisible ne désarme rien.
    """
    racine = project_path.resolve()
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return racine
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return racine
    if data.get("git_root") == "ancestor":
        return _depot_contenant(racine)
    return racine


def _depot_contenant(depart: Path) -> Path:
    """Le premier ancêtre qui porte un `.git`, ou le parent à défaut."""
    for candidat in depart.parents:
        if (candidat / ".git").exists():
            return candidat
    return depart.parent


def hors_perimetre(chemin: str, project_path: Path) -> bool:
    """True si écrire `chemin` sortirait du périmètre de ce projet.

    Les deux côtés sont résolus — liens symboliques compris. Les projets sont
    souvent des symlinks vers leur vrai emplacement : comparer les chemins non
    résolus refuserait le projet à lui-même. Et `is_relative_to` compare des
    segments, là où un préfixe de chaîne laisserait `client-a` ouvrir
    `client-attaque`.
    """
    racine = racine_autorisee(project_path)
    try:
        cible = Path(chemin)
        if not cible.is_absolute():
            cible = racine / cible
        return not cible.resolve().is_relative_to(racine)
    except (OSError, ValueError):
        # Un chemin que le système refuse de résoudre n'est pas un chemin
        # qu'on laisse écrire.
        return True


#: `/dev/null`, `2>&1` : des flux, pas des fichiers du projet.
_NON_FICHIERS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


def cibles_ecrites(commande: str) -> list[str]:
    """Les fichiers qu'une ligne de shell écrit, pour les formes simples.

    `>`, `>>` et `tee`. La ligne est **tokenisée**, jamais découpée à la main :
    `grep -r 'x > y' src/` ne redirige rien, et une comparaison de caractères
    le prendrait pour une écriture — un faux refus qui priverait l'agent d'une
    commande parfaitement légitime.

    Volontairement incomplet : ce qui ne se lit pas avec certitude n'est pas
    rendu, et passera donc.
    """
    try:
        jetons = shlex.split(commande, posix=True)
    except ValueError:
        # Guillemet non fermé : on ne sait pas lire cette ligne, donc on
        # n'invente pas de cible.
        return []

    cibles: list[str] = []
    for index, jeton in enumerate(jetons):
        suivant = jetons[index + 1] if index + 1 < len(jetons) else None
        cible: str | None = None
        if jeton in (">", ">>"):
            cible = suivant
        elif jeton.startswith(">") and len(jeton) > 1:
            cible = jeton.lstrip(">")
        elif jeton == "tee" and suivant and not suivant.startswith("-"):
            cible = suivant
        if cible and cible not in _NON_FICHIERS and not cible.startswith("&"):
            cibles.append(cible)
    return cibles


def hook_refus_hors_perimetre(
    project_path: Path | None,
) -> Callable[[HookInput, str | None, HookContext], Awaitable[HookJSONOutput]]:
    """Fabrique le hook `PreToolUse` qui enferme les écritures dans le projet.

    Sans projet — les services texte→JSON tournent sans contexte et sans
    outils — le hook laisse tout passer : il n'y a pas de périmètre à tenir.
    """

    async def hook(
        entree: HookInput, tool_use_id: str | None, contexte: HookContext
    ) -> HookJSONOutput:
        if project_path is None:
            return {}
        donnees: dict[str, Any] = dict(entree)
        outil = donnees.get("tool_name")
        entrees: dict[str, Any] = donnees.get("tool_input", {})

        if outil == "Bash":
            commande = str(entrees.get("command", ""))
            fautifs = [
                c for c in cibles_ecrites(commande) if hors_perimetre(c, project_path)
            ]
            if not fautifs:
                return {}
            chemin = fautifs[0]
        elif outil in _OUTILS_QUI_ECRIVENT:
            chemin = str(entrees.get("file_path", ""))
            if not chemin or not hors_perimetre(chemin, project_path):
                return {}
        else:
            return {}

        _logger.warning(
            "ecriture_hors_perimetre_refusee",
            extra={"chemin": chemin[:200], "projet": str(project_path)},
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": ECRITURE_REFUS,
            }
        }

    return hook
