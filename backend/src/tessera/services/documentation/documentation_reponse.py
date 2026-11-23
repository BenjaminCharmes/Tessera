"""La réponse JSON d'un agent de documentation : ses modifications et sa description."""
import json

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


def _objet_json(texte: str) -> dict[str, object] | None:
    """Lit ``texte`` comme un objet JSON, ou None s'il n'en est pas un."""
    try:
        data = json.loads(texte[texte.index("{") : texte.rindex("}") + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def lire_json(contenu: str) -> dict[str, object] | None:
    """Le premier bloc clôturé qui est un objet JSON, sinon le texte entier.

    None dit « illisible », ce qui diffère d'un objet lisible et vide.
    """
    texte = contenu.strip()
    morceaux = texte.split("```")[1::2]
    for morceau in morceaux:
        data = _objet_json(morceau[4:] if morceau.startswith("json") else morceau)
        if data is not None:
            return data
    return _objet_json(texte)


def donnees_de(contenu: str, role: str) -> dict[str, object]:
    """Lit le JSON de l'agent. Une réponse illisible ne fait rien écrire."""
    data = lire_json(contenu)
    if data is None:
        _logger.warning("reponse_doc_illisible", extra={"role": role})
        return {}
    return data


def editions_depuis(donnees: dict[str, object]) -> list[dict[str, object]]:
    """Les modifications proposées dans une réponse déjà lue."""
    editions = donnees.get("editions", [])
    return list(editions) if isinstance(editions, list) else []


def editions_de(contenu: str, role: str) -> list[dict[str, object]]:
    """Les modifications que l'agent propose, ou rien si sa réponse est illisible."""
    return editions_depuis(donnees_de(contenu, role))


def refuser(role: str, motifs: list[str], refus: list[str]) -> None:
    """Journalise les éditions refusées et les verse à ``refus``."""
    if motifs:
        _logger.warning("editions_refusees", extra={"role": role, "motif": motifs})
        refus.extend(f"{role} : {m}" for m in motifs)
