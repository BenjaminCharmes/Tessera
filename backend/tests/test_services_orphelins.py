"""Un backend tué brutalement ne doit pas laisser ses services — ticket-150.

ADR-042 affirmait : « les processus sont des enfants du backend et meurent
avec lui — c'est ce qui rend inutile toute reprise après redémarrage. » C'est
vrai d'un arrêt **propre**, par le `lifespan`. Ça ne l'est pas d'un backend
tué : le `lifespan` ne s'exécute pas, et les enfants survivent.

Le test qui gardait cette garantie appelait `tout_arreter()` lui-même — donc
il vérifiait le chemin nominal, pas la garantie. Vingt-deux processus
orphelins tournaient sur la machine quand on s'en est aperçu.

Ces tests lancent un **vrai** backend enfant, le tuent sans ménagement, et
regardent ce qui survit.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

#: Le script que le sous-processus exécute : il démarre un service, écrit son
#: PID, puis attend d'être tué.
_SCENARIO = """
import asyncio, json, sys
sys.path.insert(0, {src!r})
from pathlib import Path
from tessera.services.process_registry import ProcessRegistry

async def main():
    registre = ProcessRegistry()
    service = await registre.demarrer(
        "p", "dormeur",
        '"{python}" -c "import time; time.sleep(120)"',
        Path({racine!r}),
    )
    Path({temoin!r}).write_text(json.dumps({{"pid": service.pid}}))
    await asyncio.sleep(120)

asyncio.run(main())
"""


def _vivant(pid: int) -> bool:
    """True si ce PID désigne encore un processus."""
    if os.name == "nt":
        sortie = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
        ).stdout
        return str(pid) in sortie
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.mark.skipif(
    os.name != "nt",
    reason=(
        "Le filet est un job object Windows. Hors Windows, ADR-042 ne promet "
        "que l'arrêt propre : le vérifier ici échouerait sur une garantie que "
        "personne ne donne."
    ),
)
def test_un_backend_tue_brutalement_ne_laisse_pas_son_service(
    tmp_path: Path,
) -> None:
    # Le cas vécu, et celui qu'ADR-042 croyait impossible : sans arrêt propre,
    # le service survivait à son parent, avec son port et rien pour l'arrêter.
    src = str(Path(__file__).resolve().parents[1] / "src")
    temoin = tmp_path / "temoin.json"
    script = _SCENARIO.format(
        src=src,
        python=sys.executable.replace("\\", "\\\\"),
        racine=str(tmp_path),
        temoin=str(temoin),
    )

    parent = subprocess.Popen([sys.executable, "-c", script])
    try:
        # 30 s max : sous charge (suite complète), l'import du package tessera
        # et le démarrage d'un sous-processus asyncio peuvent dépasser 10 s.
        for _ in range(300):
            if temoin.exists():
                break
            time.sleep(0.1)
        assert temoin.exists(), "le sous-processus n'a jamais démarré le service"
        pid_du_service = int(json.loads(temoin.read_text())["pid"])
        assert _vivant(pid_du_service)

        # Tué, pas arrêté : aucun `lifespan`, aucun `finally`, rien.
        parent.kill()
        parent.wait(timeout=10)
    finally:
        if parent.poll() is None:
            parent.kill()

    for _ in range(50):
        if not _vivant(pid_du_service):
            break
        time.sleep(0.2)

    assert not _vivant(pid_du_service), (
        f"le service {pid_du_service} a survécu à la mort de son parent"
    )


def test_le_filet_se_declare_et_ne_bloque_pas_le_lancement() -> None:
    # Là où la plateforme ne sait pas tuer les enfants avec le parent, le
    # service doit quand même démarrer : refuser de lancer parce que le filet
    # manque coûterait plus que le risque qu'il couvre. Mais ça se sait.
    from tessera.services.groupe_de_processus import (
        groupe_disponible,
        rattacher,
    )

    assert groupe_disponible() is (os.name == "nt")
    # Un PID qui n'existe pas : l'appel échoue, et rend False sans lever.
    assert rattacher(0) in (True, False)


def test_rattacher_ne_leve_jamais() -> None:
    # Un service lancé ne doit pas mourir parce que le filet a échoué.
    from tessera.services.groupe_de_processus import rattacher

    assert rattacher(999_999_999) is False
