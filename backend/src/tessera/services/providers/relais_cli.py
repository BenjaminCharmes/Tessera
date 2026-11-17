"""A CLI command too long for the agent account goes through a node relay — ticket-992.

`CreateProcessWithLogonW` refuse une ligne de plus de 1 024 caractères
(ticket-946). Le déport des valeurs longues dans des fichiers ne couvre que
les options qui savent lire un fichier ; `--json-schema`, que l'audit, le
reviewer et le validateur reçoivent (ADR-061), n'accepte que du JSON en ligne :
660 caractères à lui seul pour l'audit.

Quand la ligne dépasse encore, le compte lance `node relais.js relais.json` :
le relais relit la commande complète et la lance sans shell (`CreateProcess`,
32 767 caractères), entrées et sorties héritées, et rend son code de sortie.
Le processus relayé hérite du job de l'appel (ticket-943).
"""
import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from tessera.services.providers.lanceur_windows import LIMITE_LIGNE
from tessera.services.providers.noms import ProviderIndisponible

#: Le relais : il relance la commande telle quelle et rend son code de sortie.
_RELAIS_JS = """\
const { spawn } = require("child_process");
const fs = require("fs");
const commande = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const enfant = spawn(commande[0], commande.slice(1), { stdio: "inherit", windowsHide: true });
enfant.on("error", (erreur) => { process.stderr.write(`relais : ${erreur.message}\\n`); process.exit(1); });
enfant.on("exit", (code) => process.exit(code === null ? 1 : code));
"""

_NOMS_DE_NODE = ("node.exe", "node")


def _node_du_path(chemin: str) -> str | None:
    """The node executable found in a ``PATH`` string, None when absent."""
    for entree in filter(None, chemin.split(";")):
        for nom in _NOMS_DE_NODE:
            candidat = Path(entree) / nom
            if candidat.is_file():
                return str(candidat)
    return None


def relayer_si_trop_long(
    commande: Sequence[str], dossier: Path, chemin: Callable[[], str]
) -> list[str]:
    """Return ``commande``, or its relay through ``dossier`` when its line exceeds the limit.

    ``chemin`` gives the account's ``PATH``, read only when a relay is needed:
    the relay's node must come from it (ADR-086). Without one,
    ``ProviderIndisponible`` (ADR-037).
    """
    if len(subprocess.list2cmdline(list(commande))) <= LIMITE_LIGNE:
        return list(commande)
    node = _node_du_path(chemin())
    if node is None:
        raise ProviderIndisponible(
            "ligne de commande trop longue et node absent du PATH du compte : pas de relais"
        )
    script = dossier / "relais.js"
    arguments = dossier / "relais.json"
    script.write_text(_RELAIS_JS, encoding="utf-8")
    arguments.write_text(json.dumps(list(commande)), encoding="utf-8")
    return [node, str(script), str(arguments)]
