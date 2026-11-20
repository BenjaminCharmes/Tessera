"""Weekly report of what each project shipped, read from its own files — ticket-910.

No LLM, no GitHub call, nothing written: facts come from the pipeline log,
the ticket files, the git history and the optional ``memory/faits-notables.md``.
"""

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from tessera.services.noyau.git_commande import build_command
from tessera.services.projets.releve_base import FichesBase, lire_fichier_base, reference_distante, titre_de_fiche

# Les motifs du journal, nommés : le format peut évoluer (ticket-910). Une PR
# mergée s'écrit sous deux formes : l'ancienne (`[ticket-N] livraison: PR #N
# mergée`) et celle de CIWatcher (`[projet] ticket-N PR #N mergée`).
LIGNE_APPROUVE = re.compile(
    r"^- (?P<jour>\d{4}-\d{2}-\d{2}) [\d:]+ UTC — \[ticket-(?P<ticket>\d+)\] APPROVED\b"
)
LIGNE_PR_MERGEE = re.compile(
    r"^- (?P<jour>\d{4}-\d{2}-\d{2}) [\d:]+ UTC — "
    r"(?:\[ticket-\d+\] livraison: |\[[^\]]+\] ticket-\d+ )PR #(?P<pr>\d+) mergée"
)
LIGNE_FAIT = re.compile(r"^- (?P<jour>\d{4}-\d{2}-\d{2}) — (?P<texte>.+)$")


@dataclass
class ReleveProjet:
    """What one project did over the period."""

    nom: str
    tickets: list[tuple[str, str]] = field(default_factory=list)
    prs: list[str] = field(default_factory=list)
    commits: int = 0
    faits: list[str] = field(default_factory=list)
    illisibles: list[str] = field(default_factory=list)

    def a_de_l_activite(self) -> bool:
        """Tell whether the project deserves a section."""
        return bool(
            self.tickets or self.prs or self.commits or self.faits or self.illisibles
        )


def _dans_periode(jour: str, du: date, au: date) -> bool:
    return du <= date.fromisoformat(jour) <= au


def _config(projet: Path) -> dict[str, object]:
    try:
        brut = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return brut if isinstance(brut, dict) else {}


def _titre_ticket(projet: Path, numero: str, fiches: FichesBase | None = None) -> str:
    """Read the title on the remote base, else in the ticket files, else say it is missing."""
    titre = fiches.titre(numero) if fiches else None
    if titre:
        return titre
    for fichier in sorted((projet / "tickets").glob(f"**/ticket-{numero}-*.md")):
        titre = titre_de_fiche(fichier.read_text(encoding="utf-8", errors="replace"))
        if titre:
            return titre
    return "titre introuvable"


def _lignes_journal(projet: Path, ref: str | None) -> list[str] | None:
    """Base lines then the local ones not already there; ``None`` if neither is readable."""
    de_base = lire_fichier_base(projet, ref, "memory/pipeline-log.md") if ref else None
    lignes = de_base.splitlines() if de_base else []
    try:
        locales = (projet / "memory" / "pipeline-log.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        return lignes if de_base is not None else None
    vues = set(lignes)
    return lignes + [ligne for ligne in locales if ligne not in vues]


def _lire_journal(
    projet: Path, du: date, au: date, releve: ReleveProjet, ref: str | None = None
) -> None:
    lignes = _lignes_journal(projet, ref)
    if lignes is None:
        releve.illisibles.append("memory/pipeline-log.md (OSError)")
        return
    fiches = FichesBase(projet, ref) if ref else None
    for ligne in lignes:
        ok = LIGNE_APPROUVE.match(ligne)
        if ok and _dans_periode(ok.group("jour"), du, au):
            numero = ok.group("ticket")
            releve.tickets.append((numero, _titre_ticket(projet, numero, fiches)))
        pr = LIGNE_PR_MERGEE.match(ligne)
        if pr and _dans_periode(pr.group("jour"), du, au) and pr.group("pr") not in releve.prs:
            releve.prs.append(pr.group("pr"))


def _lire_faits(projet: Path, du: date, au: date) -> list[str]:
    try:
        lignes = (projet / "memory" / "faits-notables.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []  # fichier facultatif
    faits = [LIGNE_FAIT.match(ligne) for ligne in lignes]
    return [
        f"{m.group('jour')} — {m.group('texte')}"
        for m in faits
        if m and _dans_periode(m.group("jour"), du, au)
    ]


def _compter_commits(projet: Path, du: date, au: date, base: str) -> int:
    """Count commits of the period on ``base``; raise ``OSError`` if the history is unreadable."""
    cmd = [
        *build_command(("-C", str(projet), "rev-list", "--count")),
        f"--since={du.isoformat()}T00:00:00+00:00",
        f"--until={au.isoformat()}T23:59:59+00:00", base, "--",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise OSError(str(exc)) from exc
    if res.returncode != 0:
        raise OSError(res.stderr.strip() or "historique illisible")
    return int(res.stdout.strip())


def _lire_projet(projet: Path, du: date, au: date) -> ReleveProjet:
    releve = ReleveProjet(nom=projet.name)
    base = _config(projet).get("base_branch")
    ref = reference_distante(projet, base)
    _lire_journal(projet, du, au, releve, ref)
    releve.faits = _lire_faits(projet, du, au)
    cible = ref or (base if isinstance(base, str) else "HEAD")
    try:
        releve.commits = _compter_commits(projet, du, au, cible)
    except OSError as exc:
        releve.illisibles.append(f"dépôt ({exc})")
    return releve


def _rendre(releve: ReleveProjet) -> str:
    lignes = [f"## {releve.nom}", ""]
    if releve.tickets:
        lignes.append("Tickets approuvés :")
        lignes += [f"- ticket-{n} — {titre}" for n, titre in releve.tickets]
    if releve.prs:
        lignes.append("PR mergées : " + ", ".join(f"#{n}" for n in releve.prs))
    if releve.commits:
        lignes.append(f"Commits : {releve.commits}")
    lignes += [f"Fait notable : {fait}" for fait in releve.faits]
    lignes += [f"source illisible : {raison}" for raison in releve.illisibles]
    return "\n".join(lignes) + "\n"


def releve_semaine(racine: Path, du: date, au: date, exclure: Sequence[str] = ()) -> str:
    """Return the Markdown report of every project under ``racine`` for ``du``..``au`` (inclusive)."""
    exclus: list[str] = []
    blocs = [f"# Relevé du {du.isoformat()} au {au.isoformat()}\n"]
    for projet in sorted(p for p in racine.iterdir() if (p / "CLAUDE.md").is_file()):
        if projet.name in exclure or _config(projet).get("confidentiality") == "professional":
            exclus.append(projet.name)
            continue
        releve = _lire_projet(projet, du, au)
        if releve.a_de_l_activite():
            blocs.append(_rendre(releve))
    blocs.append("Projets exclus : " + (", ".join(exclus) if exclus else "aucun") + "\n")
    return "\n".join(blocs)
