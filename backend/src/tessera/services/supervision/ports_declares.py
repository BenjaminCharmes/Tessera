"""Les ports qu'un projet déclare — ticket-416.

Deux sources, aucune devinette (ADR-042) : la commande d'un service déclaré
dans `agents.json` (`--port 8026`) et le `vite.config.ts` du front
(`server.port`). Ce que le projet n'écrit nulle part n'est pas cherché.
"""
import re
from pathlib import Path

from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.services.project_loader import load_services_config
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_PORT_DE_COMMANDE = re.compile(r"(?:^|\s)--port(?:=|\s+)(\d{2,5})\b")
_PORT_DE_VITE = re.compile(r"\bport:\s*(\d{2,5})\b")

#: Le nom donné à un port lu dans `frontend/vite.config.ts` quand aucun
#: service déclaré ne pointe vers ce dossier.
NOM_DU_FRONT = "frontend"


def ports_d_une_commande(commande: str) -> list[int]:
    """Extract the ports a service command passes with `--port`."""
    return [int(p) for p in _PORT_DE_COMMANDE.findall(commande)]


def port_de_vite_config(texte: str) -> list[int]:
    """Extract the ports a `vite.config.ts` declares (`server.port`)."""
    return [int(p) for p in _PORT_DE_VITE.findall(texte)]


def _ports_de_vite_dans(dossier: Path) -> list[int]:
    config = dossier / "vite.config.ts"
    try:
        return port_de_vite_config(config.read_text(encoding="utf-8"))
    except OSError:
        return []


def ports_du_projet(racine: Path) -> dict[int, str]:
    """Every port the project declares, mapped to the name that owns it.

    Le premier propriétaire garde le port : un même numéro ne se lit qu'une
    fois. Un `cwd` qui sort du périmètre du projet est ignoré, comme au
    lancement.
    """
    ports: dict[int, str] = {}
    for declare in load_services_config(racine):
        for port in ports_d_une_commande(declare["commande"]):
            ports.setdefault(port, declare["nom"])
        if not declare["cwd"]:
            continue
        try:
            dossier = resoudre_le_cwd(racine, declare["cwd"])
        except CommandeInvalide:
            _logger.warning("cwd_ignore", extra={"service": declare["nom"]})
            continue
        for port in _ports_de_vite_dans(dossier):
            ports.setdefault(port, declare["nom"])
    for port in _ports_de_vite_dans(racine / "frontend"):
        ports.setdefault(port, NOM_DU_FRONT)
    return ports
