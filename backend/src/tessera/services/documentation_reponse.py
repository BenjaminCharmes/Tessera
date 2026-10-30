"""La réponse JSON d'un agent de documentation : ses modifications et sa description."""
import json

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def donnees_de(contenu: str, role: str) -> dict[str, object]:
    """Lit le JSON de l'agent. Une réponse illisible ne fait rien écrire."""
    texte = contenu.strip()
    if "```" in texte:
        morceaux = texte.split("```")
        texte = next(
            (m[4:] if m.startswith("json") else m for m in morceaux if "{" in m), texte
        )
    try:
        data = json.loads(texte[texte.index("{") : texte.rindex("}") + 1])
    except (json.JSONDecodeError, ValueError):
        _logger.warning("reponse_doc_illisible", extra={"role": role})
        return {}
    return data if isinstance(data, dict) else {}


def editions_depuis(donnees: dict[str, object]) -> list[dict[str, object]]:
    """Les modifications proposées dans une réponse déjà lue."""
    editions = donnees.get("editions", [])
    return list(editions) if isinstance(editions, list) else []


def editions_de(contenu: str, role: str) -> list[dict[str, object]]:
    """Les modifications que l'agent propose, ou rien si sa réponse est illisible."""
    return editions_depuis(donnees_de(contenu, role))
