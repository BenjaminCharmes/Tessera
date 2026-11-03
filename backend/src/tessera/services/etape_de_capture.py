"""The capture step of a run — ticket-618, ADR-062, mode `joindre`.

Après l'approbation et avant la livraison : l'app du run démarre depuis son
worktree sur un port libre, les écrans se capturent dans le dossier du ticket,
l'app s'arrête. Un échec — démarrage, délai, images manquantes — se journalise
et le run continue comme sans l'étape. Le jeton de session ne sort pas d'ici :
ni journal, ni événement, ni message d'erreur.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.app_du_run import (
    AppLancee,
    Demarreur,
    DemarrageEchoue,
    Sonde,
    attendre_que_l_app_reponde,
    commande_du_run,
    config_sur_le_port,
    demarrer_processus,
    port_libre,
)
from tessera.services.captures import CapturesEchouees, Executeur, app_repond, capturer
from tessera.services.controle_visuel import ControleVisuel
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_LONGUEUR_MAX_CAUSE = 300


@dataclass
class ResultatCapture:
    """How the step ended: images, the two durations, the cause of a failure."""

    images: list[str] = field(default_factory=list)
    demarrage_ms: int = 0
    capture_ms: int = 0
    cause: str | None = None


def sans_jeton(texte: str, jeton: str | None) -> str:
    """The text on one line, bounded, with the token masked."""
    propre = " ".join(texte.split())
    if jeton:
        propre = propre.replace(jeton, "***")
    return propre[:_LONGUEUR_MAX_CAUSE]


def _ms(depuis: float) -> int:
    return int((time.monotonic() - depuis) * 1000)


async def _arreter(app: AppLancee | None) -> None:
    if app is None:
        return
    try:
        await app.arreter()
    except Exception as exc:  # noqa: BLE001 — un arrêt raté ne défait pas le run
        _logger.warning("arret_app_du_run_non_confirme", extra={"erreur": str(exc)})


async def prendre_les_captures(
    controle: ControleVisuel,
    cwd: Path,
    project_id: str,
    ticket_id: str,
    jeton: str | None = None,
    *,
    demarreur: Demarreur = demarrer_processus,
    executeur: Executeur | None = None,
    sonde: Sonde = app_repond,
    choisir_port: Callable[[], int] = port_libre,
    pause_s: float = 0.5,
) -> ResultatCapture:
    """Start the app from `cwd`, capture it, stop it ; failures are returned.

    The process launched here is stopped on every exit, an exception included.
    """
    resultat = ResultatCapture()
    app: AppLancee | None = None
    demarre = False
    debut = time.monotonic()
    try:
        port = choisir_port()
        args = commande_du_run(controle.demarrage, port)
        app = await demarreur(args, cwd)
        config = config_sur_le_port(controle.captures, port)
        await attendre_que_l_app_reponde(
            app, config.url, controle.demarrage.delai_s, sonde, pause_s
        )
        demarre = True
        resultat.demarrage_ms = _ms(debut)
        debut = time.monotonic()
        resultat.images = await capturer(
            project_id, config, executeur, jeton, ticket=ticket_id
        )
    except (DemarrageEchoue, CapturesEchouees) as exc:
        resultat.cause = sans_jeton(str(exc), jeton)
    except Exception as exc:  # noqa: BLE001 — l'étape échoue, le run continue
        resultat.cause = sans_jeton(f"{type(exc).__name__}: {exc}", jeton)
    finally:
        if demarre:
            resultat.capture_ms = _ms(debut)
        else:
            resultat.demarrage_ms = _ms(debut)
        await _arreter(app)
    return resultat
