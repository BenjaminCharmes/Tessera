"""The supervisor's idempotence ledger — ticket-859, ADR-080.

A key `action:projet/cible:sha` names one thing to do on one exact state of the
project. Done (or handed to « À toi »), it is never tried again; failed, it is
counted, and a second failure in a row ends the attempts. The ledger lives in
memory and in a file of `ide_state_dir`, outside every repository, so a restart
does not repeat what a previous pass already did.

A read never raises: an absent or unreadable file is an empty ledger.
"""
import json
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

NOM_FICHIER = "superviseur_cles.json"
#: Combien de clés faites le fichier garde (les plus anciennes sortent).
CLES_GARDEES = 1000


class EtatIdempotence:
    """Keys already done, and the consecutive failures of the keys still open."""

    def __init__(self, fichier: Path | None = None) -> None:
        self._fichier = fichier
        self._faites: dict[str, None] = {}
        self._echecs: dict[str, int] = {}
        self._charger()

    def deja_faite(self, cle: str) -> bool:
        """Whether `cle` is done (or abandoned): it is not tried again."""
        return cle in self._faites

    def marquer_faite(self, cle: str) -> None:
        """Remember `cle` as done and forget its failures."""
        self._faites[cle] = None
        self._echecs.pop(cle, None)
        while len(self._faites) > CLES_GARDEES:
            del self._faites[next(iter(self._faites))]
        self._ecrire()

    def noter_echec(self, cle: str) -> int:
        """Count one more failure on `cle`; return how many in a row it now has."""
        self._echecs[cle] = self._echecs.get(cle, 0) + 1
        self._ecrire()
        return self._echecs[cle]

    def echecs(self, cle: str) -> int:
        """The failures in a row on `cle`, `0` when it never failed."""
        return self._echecs.get(cle, 0)

    def _charger(self) -> None:
        if self._fichier is None:
            return
        try:
            brut = json.loads(self._fichier.read_text(encoding="utf-8"))
            faites = brut["faites"]
            echecs = brut["echecs"]
            if not isinstance(faites, list) or not isinstance(echecs, dict):
                raise ValueError("forme inattendue")
            self._faites = {str(cle): None for cle in faites}
            self._echecs = {str(cle): int(n) for cle, n in echecs.items()}
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError):
            _logger.warning("superviseur_cles_illisibles", extra={"fichier": str(self._fichier)})

    def _ecrire(self) -> None:
        if self._fichier is None:
            return
        contenu = json.dumps({"faites": list(self._faites), "echecs": self._echecs}, ensure_ascii=False)
        try:
            self._fichier.parent.mkdir(parents=True, exist_ok=True)
            self._fichier.write_text(contenu, encoding="utf-8", newline="\n")
        except OSError:
            # La mémoire reste juste : seule la reprise après redémarrage en pâtit.
            _logger.warning("superviseur_cles_non_ecrites", extra={"fichier": str(self._fichier)})
