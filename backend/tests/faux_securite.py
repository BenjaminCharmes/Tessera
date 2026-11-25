"""A fake `SecuriteFichiers` over a dict, shared by the take-back tests — ticket-1027."""
from pathlib import Path

from tessera.services.providers.securite_fichiers import InfoSecurite

COMPTE_SID = "S-1-5-21-1-1-1-1001"
BACKEND_SID = "S-1-5-21-1-1-1-1000"


class FauxSecurite:
    """Entries default to backend-owned, DACL inherited; `lire` and `reprendre` are recorded."""

    def __init__(self) -> None:
        self.infos: dict[Path, InfoSecurite] = {}
        self.lues: list[Path] = []
        self.reprises: list[tuple[Path, bool]] = []
        self.illisibles: set[Path] = set()
        self.disparues: set[Path] = set()
        self.reprise_sans_effet: set[Path] = set()

    def sid_de(self, compte: str) -> str:
        return BACKEND_SID if compte == "backend" else COMPTE_SID

    def poser(self, chemin: Path, proprietaire: str = BACKEND_SID, protegee: bool = False) -> None:
        self.infos[chemin] = InfoSecurite(proprietaire, protegee)

    def lire(self, chemin: Path) -> InfoSecurite:
        self.lues.append(chemin)
        if chemin in self.illisibles:
            raise PermissionError(chemin)
        if chemin in self.disparues:
            raise FileNotFoundError(chemin)
        return self.infos.get(chemin, InfoSecurite(BACKEND_SID, False))

    def reprendre(self, chemin: Path, backend_sid: str, *, proprietaire_seul: bool) -> None:
        self.reprises.append((chemin, proprietaire_seul))
        if chemin in self.reprise_sans_effet:
            return
        ancienne = self.infos.get(chemin, InfoSecurite(BACKEND_SID, False))
        self.infos[chemin] = InfoSecurite(backend_sid, ancienne.dacl_protegee if proprietaire_seul else False)
