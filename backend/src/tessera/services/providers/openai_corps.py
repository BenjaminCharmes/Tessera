"""The body sent to `/chat/completions` and the result read back — ticket-669."""
import json
from typing import Any

import httpx

from tessera.services.providers.base import ProviderResult
from tessera.services.providers.noms import ProviderIndisponible

NOM = "openai_compatible"


def corps(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    *,
    stream: bool,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    requete: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if stream:
        # Sans cette option, la plupart des serveurs n'envoient aucun compteur.
        requete["stream_options"] = {"include_usage": True}
    if schema is not None:
        requete["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "reponse", "schema": schema},
        }
    return requete


def verifier_statut(reponse: httpx.Response) -> None:
    if reponse.status_code >= 400:
        raise ProviderIndisponible(
            f"Point d'accès compatible OpenAI : statut {reponse.status_code} : "
            f"{reponse.text[:200]}"
        )


def lire_json(reponse: httpx.Response) -> dict[str, Any]:
    """The JSON object of a reply, or `ProviderIndisponible` when the server
    answers something else: l'URL ne désigne pas un point d'accès compatible."""
    try:
        donnees = reponse.json()
    except ValueError as exc:
        raise ProviderIndisponible(
            "Point d'accès compatible OpenAI : réponse qui n'est pas du JSON"
        ) from exc
    if not isinstance(donnees, dict):
        raise ProviderIndisponible(
            "Point d'accès compatible OpenAI : réponse qui n'est pas un objet JSON"
        )
    return donnees


def premier_choix(donnees: dict[str, Any]) -> dict[str, Any]:
    choix = donnees.get("choices")
    if not isinstance(choix, list) or not choix or not isinstance(choix[0], dict):
        raise ProviderIndisponible(
            "Point d'accès compatible OpenAI : réponse sans `choices`"
        )
    return choix[0]


def texte_du_message(choix: dict[str, Any]) -> str:
    message = choix.get("message")
    contenu = message.get("content") if isinstance(message, dict) else None
    return contenu if isinstance(contenu, str) else ""


def _structure(
    contenu: str, fin: object, schema: dict[str, Any] | None
) -> dict[str, Any] | None:
    """The JSON object in `contenu`, or ``None``: no schema, a reply cut by
    `max_tokens` (``finish_reason == "length"``), invalid JSON or not an object."""
    if schema is None or fin == "length":
        return None
    try:
        valeur = json.loads(contenu)
    except ValueError:
        return None
    return valeur if isinstance(valeur, dict) else None


def _compteur(usage: object, cle: str) -> int:
    if not isinstance(usage, dict):
        return 0
    valeur = usage.get(cle, 0)
    return valeur if isinstance(valeur, int) else 0


def resultat(
    contenu: str, usage: object, fin: object, schema: dict[str, Any] | None
) -> ProviderResult:
    # `cost_usd` à 0.0 et non à None : None ferait calculer le coût sur la
    # grille Anthropic, au tarif par défaut, pour un modèle qui n'en est pas.
    return ProviderResult(
        structured=_structure(contenu, fin, schema),
        content=contenu,
        input_tokens=_compteur(usage, "prompt_tokens"),
        output_tokens=_compteur(usage, "completion_tokens"),
        cost_usd=0.0,
        provider_name=NOM,
    )
