"""Filesystem endpoints for the web editor — ticket-058.

`frontend/src/lib/fs.ts` works in two modes: Tauri `invoke` on the desktop, and
a REST fallback on `/api/v1/fs/*` in the browser. That fallback called routes
that did not exist, so the Monaco editor — announced since ticket-011 and
presented as working in the README — had never worked outside desktop mode.

**The confinement is the feature.** An endpoint that reads a client-supplied
path is a directory traversal hole: `?path=~/.ssh/id_rsa` would hand over the
key, and the write endpoint is worse. Every path is resolved *through symlinks*
and then checked against the workspace — resolving is what stops a link
dropped inside the workspace from pointing out of it.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from vibe_ide.config import settings
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/fs", tags=["filesystem"])

# Au-delà, on refuse plutôt que de charger le fichier en mémoire. L'éditeur
# sert à lire des tickets et du code, pas des artefacts binaires.
_MAX_READ_BYTES = 2 * 1024 * 1024


class WriteRequest(BaseModel):
    path: str
    content: str


class DirEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


def _workspace_roots() -> list[Path]:
    """Les racines autorisées : le workspace, et la cible de chaque projet lié.

    Un projet importé en mode `symlink` pointe **hors** du workspace par
    construction (ticket-025). Sa cible résolue est donc une racine légitime,
    sans quoi l'éditeur refuserait d'ouvrir les fichiers d'un projet pourtant
    importé volontairement.
    """
    workspace = settings.ide_workspace_dir.resolve()
    roots = [workspace]
    if workspace.is_dir():
        for child in workspace.iterdir():
            if child.is_symlink() and child.is_dir():
                try:
                    roots.append(child.resolve(strict=True))
                except OSError:
                    continue
    return roots


def _resolve_inside_workspace(raw_path: str) -> Path:
    """Resolve a client-supplied path and refuse anything outside the workspace.

    Resolution happens *before* the check, and follows symlinks: checking the
    raw string would let `..` segments and links planted inside the workspace
    walk straight out of it.
    """
    try:
        # `strict=False` : un fichier à créer n'existe pas encore, mais son
        # chemin doit déjà être confiné.
        resolved = Path(raw_path).resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Chemin illisible : {raw_path}") from exc

    for root in _workspace_roots():
        if resolved == root or root in resolved.parents:
            return resolved

    _logger.warning("fs_path_refused", extra={"path": str(resolved)})
    raise HTTPException(
        status_code=403,
        detail=(
            "Ce chemin est hors du workspace de vibe-ide. "
            "L'éditeur ne peut lire et écrire que les fichiers des projets gérés."
        ),
    )


@router.get("/read", response_class=PlainTextResponse)
async def read_file(path: str = Query(...)) -> str:
    resolved = _resolve_inside_workspace(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {resolved.name}")
    if resolved.is_dir():
        raise HTTPException(
            status_code=400, detail=f"'{resolved.name}' est un dossier, pas un fichier."
        )

    size = resolved.stat().st_size
    if size > _MAX_READ_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Fichier trop volumineux ({size} octets) : "
                f"la limite de l'éditeur est de {_MAX_READ_BYTES} octets."
            ),
        )

    try:
        return resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"'{resolved.name}' n'est pas un fichier texte UTF-8.",
        ) from exc


@router.put("/write", status_code=204)
async def write_file(body: WriteRequest) -> None:
    resolved = _resolve_inside_workspace(body.path)

    if resolved.is_dir():
        raise HTTPException(
            status_code=400, detail=f"'{resolved.name}' est un dossier, pas un fichier."
        )

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(body.content, encoding="utf-8")


@router.get("/list", response_model=list[DirEntry])
async def list_dir(path: str = Query(...)) -> list[DirEntry]:
    resolved = _resolve_inside_workspace(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Dossier introuvable : {resolved.name}")
    if not resolved.is_dir():
        raise HTTPException(
            status_code=400, detail=f"'{resolved.name}' est un fichier, pas un dossier."
        )

    return [
        DirEntry(name=child.name, path=str(child), is_dir=child.is_dir())
        for child in sorted(resolved.iterdir(), key=lambda c: (not c.is_dir(), c.name))
    ]
