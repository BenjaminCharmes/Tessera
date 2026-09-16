"""Artefacts vibe-ide : versionnés avec le projet, ou locaux — ticket-062.

`tickets/`, `memory/`, `CLAUDE.md` et `agents.json` vivent dans l'arborescence
du projet, donc partent dans ses commits. C'est ce qu'on veut d'un projet
personnel : les décisions sont tracées, survivent à la machine, se partagent.

Ce n'est pas du tout ce qu'on veut d'un dépôt client. Les y pousser encombre
son dépôt de fichiers qui ne le concernent pas, expose l'organisation interne
du travail, et laisse une trace de la méthode employée — ce que ticket-060
cherche précisément à éviter par ailleurs.

Il n'y a pas de bon défaut universel : c'est une propriété **du projet**.

## Pourquoi `.git/info/exclude` et pas `.gitignore`

Le réflexe serait d'ajouter ces chemins au `.gitignore` du projet. C'est le
mauvais outil sur un dépôt client : `.gitignore` est **lui-même versionné**.
Le modifier produit un diff visible, qui annonce exactement ce qu'on voulait
taire.

`.git/info/exclude` a la même sémantique, mais reste local au clone et n'est
jamais commité. Rien n'apparaît dans l'historique ni dans un diff.
"""
import asyncio
import json
from pathlib import Path
from typing import Literal

from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

ArtifactMode = Literal["tracked", "local"]

#: Ce que vibe-ide ajoute à un projet, et qui peut ne pas avoir sa place dans
#: le dépôt de quelqu'un d'autre.
VIBE_ARTIFACT_PATHS: tuple[str, ...] = ("tickets/", "memory/", "CLAUDE.md", "agents.json")

# Les lignes ajoutées à `.git/info/exclude` sont encadrées par ces marqueurs,
# pour pouvoir les retirer sans toucher à ce que l'utilisateur y a mis.
_BEGIN = "# --- vibe-ide : artefacts locaux (ticket-062) ---"
_END = "# --- fin vibe-ide ---"


def default_mode_for(origin: str) -> ArtifactMode:
    """Le défaut selon la façon dont le projet est arrivé.

    Seul un projet **créé** par l'IDE part d'un dossier vide qui n'appartient
    qu'à l'utilisateur : ses artefacts sont versionnés.

    Un projet cloné ou **importé** existait avant vibe-ide, et souvent avant
    l'utilisateur — c'est régulièrement le dépôt d'un client. Ses artefacts
    restent locaux. On peut toujours choisir de les partager ensuite ; on ne
    peut pas défaire un push.
    """
    return "tracked" if origin == "create" else "local"


def read_artifact_mode(project_path: Path) -> ArtifactMode:
    """Le mode déclaré dans `agents.json`, `local` à défaut.

    Le défaut est **fermé**, et il a changé : `tracked` était le comportement
    historique, mais il fait reposer la confidentialité sur une déclaration
    que rien ne garantit — un `agents.json` antérieur à ticket-062, illisible,
    ou simplement absent, suffisait à pousser `tickets/` et `memory/` dans le
    dépôt de quelqu'un d'autre.

    Les deux erreurs ne se valent pas : des artefacts non versionnés se
    rattrapent d'un clic, un push ne se défait pas. Un projet qui veut
    partager ses artefacts le déclare explicitement.
    """
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return "local"
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _logger.warning("agents_json_illisible", extra={"path": str(agents_json)})
        return "local"
    return "tracked" if data.get("vibe_artifacts") == "tracked" else "local"


async def apply_artifact_mode(project_path: Path, mode: ArtifactMode) -> None:
    """Applique le mode : exclusion locale, et consignation dans `agents.json`."""
    _write_exclude(project_path, mode)
    _store_mode(project_path, mode)


def _write_exclude(project_path: Path, mode: ArtifactMode) -> None:
    exclude = project_path / ".git" / "info" / "exclude"
    if not exclude.parent.is_dir():
        # Pas de dépôt : rien à exclure, le mode reste consigné pour plus tard.
        return

    existing = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    cleaned = _without_our_block(existing)

    if mode == "local":
        block = "\n".join([_BEGIN, *VIBE_ARTIFACT_PATHS, _END])
        cleaned = f"{cleaned.rstrip()}\n{block}\n" if cleaned.strip() else f"{block}\n"

    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(cleaned, encoding="utf-8")


def _without_our_block(content: str) -> str:
    """Retire notre bloc, en préservant tout ce que l'utilisateur a écrit."""
    if _BEGIN not in content:
        return content
    kept: list[str] = []
    inside = False
    for line in content.splitlines():
        if line.strip() == _BEGIN:
            inside = True
            continue
        if line.strip() == _END:
            inside = False
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept).rstrip() + ("\n" if kept else "")


def _store_mode(project_path: Path, mode: ArtifactMode) -> None:
    agents_json = project_path / "agents.json"
    data: dict[str, object] = {}
    if agents_json.is_file():
        try:
            data = json.loads(agents_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    agents_json.write_text(
        json.dumps({**data, "vibe_artifacts": mode}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


async def tracked_artifact_paths(project_path: Path) -> list[str]:
    """Les artefacts déjà suivis par git.

    Passer en `local` ne suffit pas pour eux : git continue de suivre ce qui
    est déjà dans l'index, quelle que soit l'exclusion. Les retirer demande un
    `git rm --cached`, qui se propose — il ne se fait pas en silence.
    """
    proc = await asyncio.create_subprocess_exec(
        "git", "ls-files", "--", *VIBE_ARTIFACT_PATHS,
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        return []
    return [line for line in out.decode("utf-8", errors="replace").splitlines() if line]
