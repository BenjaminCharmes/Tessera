"""The body sent to Ollama's `/api/chat` and the result read back — ticket-189, ticket-612."""
import json
from typing import Any

import httpx

from tessera.services.providers.base import ProviderResult
from tessera.services.providers.noms import ProviderIndisponible

#: Le défaut d'Ollama est 4 096 tokens de contexte : le diff de 16 000
#: caractères que reçoit l'audit sécurité serait tronqué en silence, et le
#: verdict porterait sur sa moitié. Toujours envoyé, jamais en dessous.
NUM_CTX_MINIMUM = 16_384
#: Estimation grossière, volontairement pessimiste : un token vaut environ
#: trois caractères de code ou de français.
CARACTERES_PAR_TOKEN = 3


def _corps(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    *,
    stream: bool,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    num_ctx = max(
        NUM_CTX_MINIMUM, (len(system) + len(user)) // CARACTERES_PAR_TOKEN + max_tokens
    )
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    corps: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"num_ctx": num_ctx, "num_predict": max_tokens},
    }
    # Le champ `format` d'Ollama contraint la génération au schéma.
    if schema is not None:
        corps["format"] = schema
    return corps


def _verifier_statut(reponse: httpx.Response) -> None:
    if reponse.status_code >= 400:
        raise ProviderIndisponible(
            f"Ollama a répondu {reponse.status_code} : {reponse.text[:200]}"
        )


def _structure(
    contenu: str, donnees: dict[str, Any], schema: dict[str, Any] | None
) -> dict[str, Any] | None:
    """The JSON object in `contenu`, or ``None``: no schema, a reply cut by
    `num_predict` (``done_reason == "length"``), invalid JSON or not an object."""
    if schema is None or donnees.get("done_reason") == "length":
        return None
    try:
        valeur = json.loads(contenu)
    except ValueError:
        return None
    return valeur if isinstance(valeur, dict) else None


def _resultat(
    contenu: str, donnees: dict[str, Any], schema: dict[str, Any] | None = None
) -> ProviderResult:
    return ProviderResult(
        structured=_structure(contenu, donnees, schema),
        content=contenu,
        input_tokens=int(donnees.get("prompt_eval_count", 0) or 0),
        output_tokens=int(donnees.get("eval_count", 0) or 0),
        cost_usd=0.0,
        provider_name="ollama",
    )
