"""Proposes the coder bench candidates from the history (ticket-1053, ADR-095).

Reads `git log` of the base branch, applies the exclusions of the design (§2)
and writes the candidates with their freeze sum. Read-only git; nothing is
replayed and no model is called. Imports nothing from `tessera`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from banc_codeur_corpus import (
    Entree, chemin_du_ticket, git, somme_gel, somme_texte, texte_ticket,
)

PERIMETRE = ("backend/", "scripts/", "projects/ide-core/")
MIN_LIGNES, MAX_LIGNES = 30, 600

_SUJET = re.compile(r"^(?:feat|fix|chore)(?:\([^)]*\))?!?: ticket-(\d+)\b")
_PREUVE = re.compile(r"^preuve_reelle:\s*true\s*$", re.MULTILINE)
_ENTETE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


@dataclass(frozen=True)
class Ecart:
    """A merge left out of the corpus, with the reason."""

    ticket: str
    sha: str
    motif: str


def _zone_exclue(chemin: str) -> bool:
    nom = chemin.rsplit("/", 1)[-1]
    bas = chemin.lower()
    return (
        "worktrees/" in bas or "compte" in bas or nom == "agents.json"
        or bas.startswith(".github/") or "hooks/" in bas
        or "secret" in bas or "coffre" in bas
    )


def _est_test(chemin: str) -> bool:
    return "/tests/" in f"/{chemin}" or chemin.rsplit("/", 1)[-1].startswith("test_")


def motif_exclusion(lignes: dict[str, int], preuve_reelle: bool) -> str | None:
    """Reason to drop a diff (path -> added lines), or None when it qualifies."""
    if preuve_reelle:
        return "preuve_reelle"
    for chemin in sorted(lignes):
        if _zone_exclue(chemin):
            return f"zone exclue : {chemin}"
    for chemin in sorted(lignes):
        if chemin.startswith("frontend/"):
            return f"frontend : {chemin}"
        if not chemin.startswith(PERIMETRE):
            return f"hors périmètre : {chemin}"
    if not any(_est_test(c) for c in lignes):
        return "aucun fichier de test"
    total = sum(lignes.values())
    if not MIN_LIGNES <= total <= MAX_LIGNES:
        return f"{total} lignes ajoutées, hors de {MIN_LIGNES} à {MAX_LIGNES}"
    return None


def _lignes_ajoutees(depot: Path, base: str, sha: str) -> dict[str, int]:
    sortie = git(depot, "diff", "--numstat", "--no-renames", base, sha)
    resultat: dict[str, int] = {}
    for ligne in sortie.stdout.decode("utf-8", "replace").splitlines():
        ajoutees, _, chemin = ligne.split("\t", 2)
        resultat[chemin] = int(ajoutees) if ajoutees.isdigit() else 0
    return resultat


def _preuve_reelle(texte_brut: str) -> bool:
    entete = _ENTETE.match(texte_brut.replace("\r\n", "\n"))
    return bool(entete and _PREUVE.search(entete.group(1)))


def _merges(depot: Path, branche: str) -> list[tuple[str, str, str]]:
    """(sha, premier parent, ticket) of each ticket squash, newest first."""
    sortie = git(depot, "log", "--first-parent", "--format=%H%x09%P%x09%s", branche)
    merges: list[tuple[str, str, str]] = []
    for ligne in sortie.stdout.decode("utf-8", "replace").splitlines():
        sha, parents, sujet = (ligne.split("\t", 2) + ["", ""])[:3]
        trouve = _SUJET.match(sujet)
        if trouve and parents:
            merges.append((sha, parents.split()[0], trouve.group(1)))
    return merges


def candidat(depot: Path, sha: str, base: str, numero: str) -> Entree | Ecart:
    """The entry for one squash, or the reason it is left out."""
    ticket = f"ticket-{numero}"
    chemin = chemin_du_ticket(depot, base, numero)
    if chemin is None:
        return Ecart(ticket, sha, "ticket absent à la base")
    lu = git(depot, "show", f"{base}:{chemin}").stdout.decode("utf-8", "replace")
    lignes = _lignes_ajoutees(depot, base, sha)
    motif = motif_exclusion(lignes, _preuve_reelle(lu))
    if motif is not None:
        return Ecart(ticket, sha, motif)
    return Entree(
        id=sha[:12], ticket=ticket, sha=sha, base_sha=base, ticket_chemin=chemin,
        ticket_sha256=somme_texte(texte_ticket(depot, base, chemin)),
        fichiers=tuple(sorted(lignes)), lignes_ajoutees=sum(lignes.values()), pilote=False,
    )


def proposer(
    depot: Path, branche: str, taille: int, pilote: int
) -> tuple[list[Entree], list[Ecart]]:
    """Newest-first candidates; the `pilote` oldest of them are flagged outside the freeze."""
    retenues: list[Entree] = []
    ecartes: list[Ecart] = []
    for sha, base, numero in _merges(depot, branche):
        if len(retenues) >= taille + pilote:
            break
        resultat = candidat(depot, sha, base, numero)
        if isinstance(resultat, Entree):
            retenues.append(resultat)
        else:
            ecartes.append(resultat)
    debut_pilote = max(len(retenues) - pilote, 0)
    for rang in range(debut_pilote, len(retenues)):
        retenues[rang] = replace(retenues[rang], pilote=True)
    return retenues, ecartes


def ecrire(sortie: Path, entrees: list[Entree], ecartes: list[Ecart]) -> None:
    contenu = {
        "gel_sha256": somme_gel(entrees),
        "entrees": [asdict(e) for e in entrees],
        "ecartes": [asdict(e) for e in ecartes],
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(contenu, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description="Propose the coder bench candidates.")
    analyseur.add_argument("--depot", type=Path, default=Path("."))
    analyseur.add_argument("--branche", default="develop")
    analyseur.add_argument("--taille", type=int, default=20)
    analyseur.add_argument("--pilote", type=int, default=3)
    analyseur.add_argument("--sortie", type=Path, default=Path("docs/essais/banc-codeur/corpus.json"))
    args = analyseur.parse_args(argv)
    entrees, ecartes = proposer(args.depot, args.branche, args.taille, args.pilote)
    ecrire(args.sortie, entrees, ecartes)
    sys.stdout.write(f"{len(entrees)} candidat(s), {len(ecartes)} écarté(s) -> {args.sortie}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
