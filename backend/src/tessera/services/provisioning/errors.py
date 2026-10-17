"""The only error a service client raises — ticket-465.

An API error body can repeat the value that was sent (a key, a variable), so
the message keeps the HTTP status and the API's error code, and nothing else.
"""
import json
import re

#: A code is a short identifier; anything else is not trusted as one.
_CODE_VALIDE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

CODE_INCONNU = "unknown"

_REASON_MAX = 300
_MASQUE = "[redacted]"
_URL = re.compile(r"\S+://\S+")


class ServiceError(Exception):
    """A service call failed: which service, the HTTP status, the error code.

    ``reason`` is the API's own explanation, only set by a client that opts in
    through ``from_response(..., with_reason=True)``.
    """

    def __init__(
        self, service: str, status: int, code: str = CODE_INCONNU, reason: str = ""
    ) -> None:
        self.service = service
        self.status = status
        self.code = code if _CODE_VALIDE.match(code) else CODE_INCONNU
        self.reason = reason
        suite = f": {reason}" if reason else ""
        super().__init__(f"{service}: HTTP {status} ({self.code}){suite}")

    @classmethod
    def from_response(
        cls,
        service: str,
        status: int,
        body: str | bytes,
        with_reason: bool = False,
        redact: tuple[str, ...] = (),
    ) -> "ServiceError":
        """Build the error from a response body.

        By default only the error code is kept. With ``with_reason`` the
        ``message`` field comes along, cleaned by ``reason_from_body``.
        """
        reason = reason_from_body(body, redact) if with_reason else ""
        return cls(service, status, code_from_body(body), reason)


def _code_candidat(corps: object) -> object:
    """Locate the error code in the shapes the five APIs use."""
    if not isinstance(corps, dict):
        return None
    erreur = corps.get("error")
    # Une erreur en simple chaîne n'est jamais lue : c'est un message, pas un code.
    if isinstance(erreur, dict):
        return erreur.get("code") or erreur.get("type")
    erreurs = corps.get("errors")
    if isinstance(erreurs, list) and erreurs and isinstance(erreurs[0], dict):
        return erreurs[0].get("code")
    return corps.get("code") or corps.get("name")


def reason_from_body(body: str | bytes, redact: tuple[str, ...] = ()) -> str:
    """Extract the ``message`` field of an error body, cleaned and bounded.

    Anything that looks like a URL (a connection URI carries a password) and
    every value of ``redact`` is replaced; the text is cut to ``_REASON_MAX``.
    """
    try:
        corps = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return ""
    message = corps.get("message") if isinstance(corps, dict) else None
    if not isinstance(message, str):
        return ""
    texte = _URL.sub(_MASQUE, " ".join(message.split()))
    for valeur in redact:
        if valeur.strip():
            texte = texte.replace(valeur, _MASQUE)
    return texte[:_REASON_MAX]


def code_from_body(body: str | bytes) -> str:
    """Extract the API error code from a response body, or ``unknown``."""
    try:
        candidat = _code_candidat(json.loads(body))
    except (ValueError, UnicodeDecodeError):
        return CODE_INCONNU
    if isinstance(candidat, (str, int)) and _CODE_VALIDE.match(str(candidat)):
        return str(candidat)
    return CODE_INCONNU
