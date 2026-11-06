"""Contrôle déterministe des secrets dans le diff avant push — ticket-547.

Un push ne sort pas si une ligne ajoutée porte la forme d'un secret reconnu
(clé AWS, jeton GitHub ou GitLab, clé Anthropic ou Stripe, clé privée,
identifiants dans une URL), ou si le diff ajoute un fichier `.env`, `*.pem` ou
`id_rsa`. Aucun modèle n'intervient : ce sont des expressions régulières.

Contrairement aux termes interdits (ADR-048), aucune exemption : un dépôt
professionnel n'a pas plus le droit de publier une clé.

Comme pour les termes interdits, la sortie nomme le fichier, la ligne et le
type de secret, jamais la valeur : un log se partage.
"""
from __future__ import annotations

import posixpath
import re
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ViolationSecret:
    """Where a secret-shaped string was found; never the string itself."""

    fichier: str
    ligne: int
    type_secret: str

    def __str__(self) -> str:
        return f"{self.fichier}:{self.ligne} ({self.type_secret})"


@dataclass(frozen=True)
class _Ajout:
    """One element of a diff: an added file header or an added line."""

    fichier: str
    ligne: int
    contenu: str | None  # None : en-tête d'un fichier ajouté ou modifié
    illisible: bool = False  # en-tête `+++` dont le chemin n'a pas pu être lu


_ENTETE_ILLISIBLE = "unreadable-diff-header"
_ECHAPPEMENTS = {
    "a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92,
}
_OCTAL = re.compile(r"[0-3][0-7]{2}")

# Les motifs d'en-tête de clé privée sont assemblés pour que ce fichier ne se
# reconnaisse pas lui-même quand il traverse le contrôle.
_DEBUT_CLE = "-----" + "BEGIN "
_URL_EXCLUS = r"\s/:@{}<>$'\""

_MOTIFS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("github-token", re.compile(r"github_pat_[A-Za-z0-9_]{22,}")),
    ("gitlab-token", re.compile(r"glpat-[A-Za-z0-9_-]{20,}")),
    ("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("stripe-live-key", re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
    ("private-key", re.compile(_DEBUT_CLE + r"[A-Z ]*PRIVATE KEY-----")),
    # Un mot de passe de documentation (`password`, `changeme`, `xxx`…) n'est
    # pas un secret : sans cette exception, la doc de l'URL se bloquerait.
    (
        "url-credentials",
        re.compile(
            rf"://[^{_URL_EXCLUS}]+:"
            rf"(?!(?:password|passwd|pass|secret|changeme|x+|\*+)@)"
            rf"[^{_URL_EXCLUS}]+@",
            re.IGNORECASE,
        ),
    ),
)

_ENTETE_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _type_de_fichier(chemin: str) -> str | None:
    """The secret type a file name implies, or None for an ordinary file."""
    nom = posixpath.basename(chemin)
    if nom == ".env":
        return "env-file"
    if nom.endswith(".pem"):
        return "pem-file"
    if nom == "id_rsa":
        return "ssh-private-key-file"
    return None


def _types_dans_ligne(contenu: str) -> list[str]:
    """The distinct secret types a line matches, in declaration order."""
    types: list[str] = []
    for type_secret, motif in _MOTIFS:
        if type_secret not in types and motif.search(contenu):
            types.append(type_secret)
    return types


def _decoder_chemin_cite(cite: str) -> str | None:
    """Decode a path git quoted (``"b/na\\303\\257f.py"``), or None if malformed."""
    corps = cite[1:-1]
    octets = bytearray()
    i = 0
    while i < len(corps):
        c = corps[i]
        if c == '"':
            return None
        if c != "\\":
            octets += c.encode("utf-8")
            i += 1
        elif _OCTAL.fullmatch(corps[i + 1:i + 4]):
            octets.append(int(corps[i + 1:i + 4], 8))
            i += 4
        elif corps[i + 1:i + 2] in _ECHAPPEMENTS:
            octets.append(_ECHAPPEMENTS[corps[i + 1]])
            i += 2
        else:
            return None
    return octets.decode("utf-8", errors="replace")


def _fichier_de_l_entete(cible: str) -> str | None:
    """The new-file path of a ``+++`` target, or None when it cannot be read."""
    if len(cible) >= 2 and cible[0] == cible[-1] == '"':  # noqa: PLR2004
        decode = _decoder_chemin_cite(cible)
        cible = decode if decode is not None else ""
    return cible[2:] if cible.startswith("b/") and len(cible) > 2 else None  # noqa: PLR2004


def _parcourir(diff: str) -> Iterator[_Ajout]:
    """Walk a unified diff and yield file headers and added lines.

    The line number is the one in the new file. Inside a hunk, a line that
    begins with ``+++`` is content, not a header: only ``diff --git`` leaves
    the hunk. A ``+++`` header other than ``/dev/null`` whose path cannot be
    read is yielded as unreadable: its added lines would be skipped, so the
    caller refuses the diff instead.
    """
    fichier: str | None = None
    ligne = 0
    dans_hunk = False
    for brut in diff.splitlines():
        if brut.startswith("diff --git "):
            fichier, dans_hunk = None, False
        elif not dans_hunk and brut.startswith("+++ "):
            cible = brut[4:].strip()
            fichier = _fichier_de_l_entete(cible)
            if fichier:
                yield _Ajout(fichier, 1, None)
            elif cible != "/dev/null":
                yield _Ajout(cible, 1, None, illisible=True)
        elif (entete := _ENTETE_HUNK.match(brut)) is not None:
            dans_hunk, ligne = True, int(entete.group(1))
        elif dans_hunk and fichier and brut.startswith("+"):
            yield _Ajout(fichier, ligne, brut[1:])
            ligne += 1
        elif dans_hunk and (brut.startswith(" ") or brut == ""):
            ligne += 1


def chercher_secrets(diff: str) -> list[ViolationSecret]:
    """Return the secret-shaped additions found in a unified diff.

    Only added lines count: a removed line, or a context line, is ignored.
    A `.env`, `*.pem` or `id_rsa` file header is reported on line 1, and so is
    a `+++` header whose path cannot be read (type `unreadable-diff-header`):
    the gate fails closed (ADR-039).
    """
    violations: list[ViolationSecret] = []
    for ajout in _parcourir(diff):
        if ajout.illisible:
            violations.append(ViolationSecret(ajout.fichier, 1, _ENTETE_ILLISIBLE))
            continue
        if ajout.contenu is None:
            type_fichier = _type_de_fichier(ajout.fichier)
            if type_fichier is not None:
                violations.append(ViolationSecret(ajout.fichier, 1, type_fichier))
            continue
        for type_secret in _types_dans_ligne(ajout.contenu):
            violations.append(
                ViolationSecret(ajout.fichier, ajout.ligne, type_secret)
            )
    return violations


def refus_secrets(diff: str) -> str | None:
    """Return the refusal message for a diff that carries secrets, else None.

    No exemption applies: ``confidentialite == "professional"`` waives the
    forbidden-terms check, not this one. The message names file, line and
    type, never the value.
    """
    violations = chercher_secrets(diff)
    if not violations:
        return None
    sources = ", ".join(str(v) for v in violations)
    return f"Push bloqué : secret détecté. Sources : {sources}"
