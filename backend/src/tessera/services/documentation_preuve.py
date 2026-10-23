"""Le contrôle des faits d'une édition de documentation — ticket-542, ADR-057.

Jusqu'ici `appliquer_editions` ne vérifiait qu'une chose : que l'`ancien` texte
existe. Rien ne vérifiait le `nouveau`, et un modèle y glissait des numéros
d'ADR, des seuils ou des noms de format qu'aucun code ne portait. Ce module
rend le contrôle mécanique : une édition cite le code livré qui la fonde
(`preuve`), les jetons qu'elle introduit doivent figurer dans la matière
fournie à l'agent, et son volume est borné.

Limite connue : un extrait qui existe ne prouve pas qu'il soutient la phrase.
Le contrôle écarte les faits sans origine dans le code ; il ne remplace pas la
relecture, à qui il donne la citation à vérifier.
"""
import re
from re import Match, Pattern

from tessera.services.documentation_base import EditionRefusee, normaliser_typo
from tessera.services.documentation_code import MatiereCode

#: Ce qu'une édition `ancien`/`nouveau` a le droit de remplacer, en caractères,
#: et ce qu'un rôle remplace sur un lot. À ajuster après les premiers lots.
VOLUME_MAX_EDITION = 2_000
VOLUME_MAX_ROLE = 8_000

Jeton = tuple[str, str]

_UNITES = r"(?:[KMGT]i?[oB]|ko|ms|min|s|h|jours?|px|%|caractères|tokens)"
_FORMATS = (
    "GIF|AVIF|PNG|JPE?G|WEBP|SVG|BMP|TIFF|HEIC|ICO|PDF|MP3|MP4|WEBM|ZIP|DOCX|XLSX|CSV"
)

#: Les familles de jetons vérifiables : (famille, motif). Le nombre porte deux
#: groupes (valeur, unité), les autres un seul.
_MOTIFS: tuple[tuple[str, Pattern[str]], ...] = (
    ("adr", re.compile(r"\bADR-(\d+)", re.I)),
    ("ticket", re.compile(r"\bticket-(\d+)", re.I)),
    ("nombre", re.compile(rf"(?<![\w.,])(\d+(?:[.,]\d+)?)\s?({_UNITES})(?![\wÀ-ÿ])")),
    ("migration", re.compile(r"\bmigrations?\s+(?:n[°o]\s*)?(\d{3,4})\b", re.I)),
    ("migration", re.compile(r"(?<![\w])(\d{4})_[A-Za-z]")),
    ("extension", re.compile(rf"\b({_FORMATS})\b")),
    ("guillemets", re.compile(r'"\s*([^"\n\s][^"\n]{0,39}?)\s*"')),
)


def aplatir(texte: str) -> str:
    """Typography flattened and whitespace collapsed, for tolerant comparison."""
    plat, _ = normaliser_typo(texte)
    return re.sub(r"\s+", " ", plat).strip()


def _valeur(famille: str, trouve: Match[str]) -> str:
    if famille == "nombre":
        return f"{trouve.group(1).replace(',', '.')} {trouve.group(2)}"
    if famille == "extension":
        return trouve.group(1).lower()
    if famille == "guillemets":
        return aplatir(trouve.group(1)).lower()
    numero = int(trouve.group(1))
    if famille == "adr":
        return f"ADR-{numero}"
    if famille == "ticket":
        return f"ticket-{numero}"
    return f"{numero:04d}"


def jetons_de(texte: str) -> set[Jeton]:
    """The verifiable tokens of ``texte``: ADR and ticket numbers, quantities, etc."""
    plat, _ = normaliser_typo(texte)
    return {
        (famille, _valeur(famille, trouve))
        for famille, motif in _MOTIFS
        for trouve in motif.finditer(plat)
    }


def _texte_du_code(matiere: MatiereCode) -> str:
    """The diffs and the file contents: where an extract may be found."""
    diffs = (diff.diff for diff in matiere.diffs)
    fichiers = (fichier.contenu for fichier in matiere.fichiers)
    return "\n".join([*diffs, *fichiers])


def fichiers_de_la_matiere(matiere: MatiereCode) -> list[str]:
    """Every file the agent was given, shown or not, sorted and without duplicates."""
    noms: set[str] = set(matiere.fichiers_non_montres)
    noms.update(fichier.chemin for fichier in matiere.fichiers)
    for diff in matiere.diffs:
        noms.update(diff.fichiers)
    return sorted(noms)


def _chaine(edition: dict[str, object], cle: str) -> str:
    valeur = edition.get(cle)
    return "" if valeur is None else str(valeur)


class ControleDePreuve:
    """Checks the editions of one role on one batch against the material it was given.

    ``matiere`` is the code the agent read and ``tickets`` the text of the
    tickets. The current documentation is deliberately not part of it: it is
    what carries the errors to correct. The instance keeps the volume replaced
    so far, so one instance serves one role, one call.
    """

    def __init__(self, matiere: MatiereCode, tickets: str = "") -> None:
        code = _texte_du_code(matiere)
        self._code = aplatir(code)
        tout = aplatir(tickets + "\n" + code).lower()
        self._tout = tout
        self._jetons = jetons_de(tickets + "\n" + code)
        self._remplace = 0

    def verifier(self, edition: dict[str, object], chemin: str) -> None:
        """Raise `EditionRefusee`, naming the rule, if the edition breaks one."""
        self._volume(edition, chemin)
        if self._est_un_retrait(edition):
            return
        self._preuve(edition, chemin)
        self._jetons_nouveaux(edition, chemin)

    @staticmethod
    def _est_un_retrait(edition: dict[str, object]) -> bool:
        remplace = "contenu" not in edition and "apres_section" not in edition
        return remplace and "nouveau" in edition and not _chaine(edition, "nouveau").strip()

    def _volume(self, edition: dict[str, object], chemin: str) -> None:
        if "contenu" in edition or "apres_section" in edition:
            return
        taille = len(_chaine(edition, "ancien"))
        if taille > VOLUME_MAX_EDITION:
            raise EditionRefusee(
                f"{chemin} : règle « volume » — l'édition remplace {taille} caractères, "
                f"au plus {VOLUME_MAX_EDITION}. Une réécriture large n'est pas liée à un "
                "ticket : coupe-la en retouches ciblées, ou ne la fais pas."
            )
        self._remplace += taille
        if self._remplace > VOLUME_MAX_ROLE:
            raise EditionRefusee(
                f"{chemin} : règle « volume » — ce lot remplace {self._remplace} "
                f"caractères pour ce rôle, au plus {VOLUME_MAX_ROLE}."
            )

    def _preuve(self, edition: dict[str, object], chemin: str) -> None:
        preuves = edition.get("preuve")
        if not isinstance(preuves, list) or not preuves:
            raise EditionRefusee(
                f"{chemin} : règle « preuve » — l'édition ne cite aucun code livré. "
                "Ajoute `preuve: [{fichier, extrait}]`, extrait recopié du diff ou "
                "d'un fichier fourni ; sans extrait qui la soutienne, ne l'écris pas."
            )
        for preuve in preuves:
            fichier = _chaine(preuve, "fichier").strip() if isinstance(preuve, dict) else ""
            extrait = _chaine(preuve, "extrait") if isinstance(preuve, dict) else ""
            if not fichier or not extrait.strip():
                raise EditionRefusee(
                    f"{chemin} : règle « preuve » — chaque entrée porte `fichier` et "
                    "`extrait`, tous deux non vides."
                )
            if aplatir(extrait) not in self._code:
                raise EditionRefusee(
                    f"{chemin} : règle « preuve » — l'extrait « {extrait.strip()[:60]} » "
                    f"({fichier}) n'est ni dans le diff ni dans les fichiers fournis."
                )

    def _jetons_nouveaux(self, edition: dict[str, object], chemin: str) -> None:
        ecrit = _chaine(edition, "nouveau") or _chaine(edition, "texte")
        introduits = jetons_de(ecrit) - jetons_de(_chaine(edition, "ancien"))
        for jeton in sorted(introduits):
            if not self._present(jeton):
                famille, valeur = jeton
                raise EditionRefusee(
                    f"{chemin} : règle « jeton vérifiable » — {famille} « {valeur} » "
                    "n'est ni dans le texte remplacé, ni dans les tickets, le diff ou "
                    "les fichiers fournis. Corrige-le d'après le code, ou retire-le."
                )

    def _present(self, jeton: Jeton) -> bool:
        famille, valeur = jeton
        if famille == "guillemets":
            return valeur in self._tout
        if famille == "extension":
            return re.search(rf"\b{re.escape(valeur)}\b", self._tout) is not None
        return jeton in self._jetons
