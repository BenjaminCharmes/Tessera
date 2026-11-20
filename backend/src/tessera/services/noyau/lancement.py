"""How a command declared by a project is launched, without a shell.

Deux services lancent des commandes que les projets déclarent :
`ProcessRegistry` pour leurs services (ADR-042) et `TestRunnerService` pour
leurs tests. Aucun des deux ne passe par un shell — c'est ce qui évite de
rouvrir ce qu'ADR-027 et ADR-031 ferment.

Mais sans shell, `npm` n'existe pas sous Windows : l'exécutable réel est
`npm.cmd`, et seul un shell applique `PATHEXT`. La reprise vivait dans
`ProcessRegistry` depuis le ticket-143 ; `TestRunnerService` ne l'avait pas,
et rendait `blocked` le premier ticket d'un projet dont le code était juste
(ticket-157).

C'est ADR-034 pris par l'autre bout : pas une règle décrite à deux endroits,
un **comportement** implémenté à deux endroits et corrigé à un seul. D'où ce
module : la règle est ici, et nulle part ailleurs.
"""

import os
import subprocess
from typing import Any

#: Ce qui est déjà un exécutable : inutile d'essayer d'y ajouter `.cmd`.
_DEJA_EXECUTABLE = (".cmd", ".bat", ".exe", ".com")


def essais_de_commande(args: list[str]) -> list[list[str]]:
    """Return the forms to try for this command, most direct first.

    Écrire `npm.cmd` dans un `agents.json` marcherait sur la machine qui l'a
    écrit et nulle part ailleurs — or ce fichier est versionné et part sur
    d'autres postes. Le manifeste reste donc portable, et c'est le lancement
    qui s'adapte.
    """
    if not args:
        return []
    essais = [args]
    if os.name == "nt" and not args[0].lower().endswith(_DEJA_EXECUTABLE):
        essais.append([args[0] + ".cmd", *args[1:]])
    return essais


def options_de_lancement(systeme: str) -> dict[str, Any]:
    """Isolate a service from the backend that launches it — ticket-664.

    Hors Windows, son propre groupe : c'est ce qui rend `killpg` sûr à l'arrêt.
    Sans lui, le service hérite du groupe du backend, et l'arrêter emporterait
    le backend (ticket-153).

    Sous Windows, sa propre console, sans fenêtre. Un `uvicorn --reload` qui
    recharge envoie `CTRL_C_EVENT`, et Windows le remet à **tous** les processus
    de la console : le 28/10, le rechargement du backend de Curio a arrêté trois
    fois celui de Tessera, et tous ses enfants avec.
    """
    if systeme != "nt":
        return {"start_new_session": True}
    drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
    )
    return {"creationflags": drapeaux}
