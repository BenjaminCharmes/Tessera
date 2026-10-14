"""Reconnaître un service déclaré dans la ligne de commande d'un processus — ticket-438.

Un service sans port n'a que sa commande pour se faire reconnaître. On en tire
une **signature** : le module après `-m` (avec ses arguments positionnels, pour
ne pas confondre deux `uvicorn` de cibles différentes) ou, à défaut, le script
`.py`. Une commande sans signature fiable (`npm run dev`) n'en donne pas : mieux
vaut ne rien reconnaître que reconnaître un étranger.

La signature ne prouve pas l'appartenance au projet ; elle ne sert que combinée
à `appartient_au_projet`.
"""
import os
import re

from tessera.services.sonde_systeme import InfoProcessus

_MODULE = re.compile(r"""(?:^|\s)-m\s+([A-Za-z_][\w.]*(?:\s+[^\s\-][^\s]*)*)""")
_SCRIPT = re.compile(r"""(?:^|[\s"'])([^\s"']+\.py)(?=$|[\s"'])""")
_AVANT = r"(?<![\w.\-])"
_APRES = r"(?![\w.\-])"


def _normaliser(texte: str) -> str:
    """Slashes avant, guillemets retirés, espaces repliés, casse ignorée sous Windows."""
    net = " ".join(texte.replace("\\", "/").replace('"', " ").replace("'", " ").split())
    return net.lower() if os.name == "nt" else net


def signature(commande: str) -> str | None:
    """The recognisable part of a service command, or `None` when there is none."""
    module = _MODULE.search(commande.replace('"', " ").replace("'", " "))
    if module is not None:
        return _normaliser(module.group(1))
    script = _SCRIPT.search(commande)
    return _normaliser(script.group(1)) if script is not None else None


def commande_porte(signature_du_service: str, info: InfoProcessus) -> bool:
    """Whether the process command line contains the service signature as whole tokens."""
    motif = _AVANT + re.escape(signature_du_service) + _APRES
    return re.search(motif, _normaliser(info.commande)) is not None
