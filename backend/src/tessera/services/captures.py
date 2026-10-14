"""Capture a running project's screens — ticket-432.

Le backend vérifie que l'app répond, puis délègue la prise de vue à un
exécuteur : par défaut `scripts/captures.mjs`, qui utilise le Playwright du
frontend de Tessera. Les images vont dans le dossier d'état de l'IDE, hors du
dépôt du projet (ADR-021) : une capture n'a pas à finir dans un commit.
"""
import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlsplit

from tessera.config import settings
from tessera.services.captures_config import (
    LARGEURS,
    THEMES,
    ConfigCaptures,
)
from tessera.services.lancement import essais_de_commande
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "captures.mjs"
_DELAI_SONDE_S = 2.0
_DELAI_EXECUTEUR_S = 300.0

#: Forme d'un nom de capture : `<nom>-<largeur>-<thème>.png`.
MOTIF_FICHIER = re.compile(r"^[a-z0-9-]+-(390|1440)-(clair|sombre)\.png$")

Executeur = Callable[[ConfigCaptures, Path], Awaitable[None]]


class CapturesEchouees(Exception):
    """The capture run failed or did not produce every expected image."""


def dossier_des_captures(project_id: str) -> Path:
    """Return where this project's captures live, outside its repository."""
    return settings.ide_state_dir / "captures" / project_id


def noms_attendus(config: ConfigCaptures) -> list[str]:
    """Return the `<nom>-<largeur>-<thème>.png` names, four per screen."""
    return [
        f"{ecran.nom}-{largeur}-{theme}.png"
        for ecran in config.ecrans
        for largeur in LARGEURS
        for theme in THEMES
    ]


async def app_repond(url: str) -> bool:
    """Return True when something accepts a TCP connection at this URL."""
    parties = urlsplit(url)
    if not parties.hostname:
        return False
    port = parties.port or (443 if parties.scheme == "https" else 80)
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(parties.hostname, port), _DELAI_SONDE_S
        )
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    return True


async def _lancer_le_script(
    commande: list[str], config: ConfigCaptures, sortie: Path
) -> tuple[int, str]:
    processus = await asyncio.create_subprocess_exec(
        *commande,
        str(sortie),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    charge = json.dumps(
        {
            "url": config.url,
            "largeurs": list(LARGEURS),
            "themes": list(THEMES),
            "ecrans": [
                {"nom": e.nom, "chemin": e.chemin, "clic": e.clic}
                for e in config.ecrans
            ],
        }
    ).encode("utf-8")
    _, erreurs = await processus.communicate(charge)
    return processus.returncode or 0, erreurs.decode("utf-8", "replace").strip()


async def executeur_playwright(config: ConfigCaptures, sortie: Path) -> None:
    """Run `scripts/captures.mjs` without a shell, config given on stdin."""
    for commande in essais_de_commande(["node", str(_SCRIPT)]):
        try:
            code, erreurs = await _lancer_le_script(commande, config, sortie)
        except FileNotFoundError:
            continue
        if code != 0:
            raise CapturesEchouees(erreurs or f"Le script s'est terminé en {code}.")
        return
    raise CapturesEchouees("Node est introuvable : il faut `node` dans le PATH.")


async def capturer(
    project_id: str,
    config: ConfigCaptures,
    executeur: Executeur | None = None,
) -> list[str]:
    """Capture every declared screen and return the image names, in order."""
    sortie = dossier_des_captures(project_id)
    sortie.mkdir(parents=True, exist_ok=True)
    attendus = noms_attendus(config)
    # Une image d'un tour précédent ferait passer un échec pour une réussite.
    for nom in attendus:
        (sortie / nom).unlink(missing_ok=True)
    try:
        lancer = executeur or executeur_playwright
        await asyncio.wait_for(lancer(config, sortie), _DELAI_EXECUTEUR_S)
    except asyncio.TimeoutError as exc:
        raise CapturesEchouees(
            f"Les captures n'ont pas fini en {int(_DELAI_EXECUTEUR_S)} s."
        ) from exc
    manquantes = [nom for nom in attendus if not (sortie / nom).is_file()]
    if manquantes:
        raise CapturesEchouees(f"Captures manquantes : {', '.join(manquantes)}.")
    _logger.info("captures_prises", extra={"projet": project_id, "nombre": len(attendus)})
    return attendus
