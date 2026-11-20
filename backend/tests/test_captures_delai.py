"""A cancelled capture script is killed, not left running — ticket-883.

`capturer` borne l'exécuteur par `asyncio.wait_for` : au délai, la tâche est
annulée dans `_lancer_le_script`, et node ne doit pas lui survivre.
"""
import asyncio
import sys
from pathlib import Path

import pytest

from tessera.services.verification import captures
from tessera.services.verification.captures_config import ConfigCaptures, Ecran

_DORMEUR = [sys.executable, "-c", "import time; time.sleep(60)"]


async def _attendre_le_processus(lances: list[asyncio.subprocess.Process]) -> None:
    for _ in range(200):
        if lances:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("Le faux script ne s'est pas lancé.")


@pytest.mark.asyncio
async def test_cancelled_script_is_killed_and_cancellation_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lances: list[asyncio.subprocess.Process] = []
    creer = asyncio.create_subprocess_exec

    async def espion(*args: str, **kwargs: object) -> asyncio.subprocess.Process:
        processus = await creer(*args, **kwargs)  # type: ignore[arg-type]
        lances.append(processus)
        return processus

    monkeypatch.setattr(captures.asyncio, "create_subprocess_exec", espion)
    config = ConfigCaptures(url="http://localhost:1", ecrans=(Ecran(nom="accueil", chemin="/"),))

    tache = asyncio.create_task(captures._lancer_le_script(_DORMEUR, config, tmp_path, None))
    await _attendre_le_processus(lances)
    tache.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tache
    assert lances[0].returncode is not None
