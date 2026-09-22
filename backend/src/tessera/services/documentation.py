"""Mettre à jour la documentation par lot, en modifications ciblées — t.092.

Deux défauts corrigés d'un coup.

**Le premier était une mine.** L'agent de documentation d'origine tournait à
chaque run approuvé, ne
voyait la documentation que tronquée à 8 000 caractères, ne pouvait en émettre
que ~8 000 (2048 tokens), et réécrivait le fichier **entier** avec ce qu'il
avait produit. Sur un `README.md` de 24 000 caractères, le premier run activé
en aurait effacé les deux tiers, sans erreur. Il ne pouvait pas faire
autrement : le contrat le lui imposait.

Ici le contrat est inverse. L'agent rend des **modifications** — un ancien
texte, un nouveau — et rien d'autre ne s'écrit. Un ancien texte absent,
ambigu, ou qui amputerait le fichier fait tout échouer, sans rien écrire.

**Le second était le rythme.** Documenter à chaque ticket réécrit le même
fichier trois fois pour une même feature. La documentation décrit le produit,
pas un changement : elle se met à jour par **lot**, une fois par file de
tickets, ce qui divise d'autant le nombre d'appels.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from tessera.services.providers.base import LLMProvider
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_MARQUEUR = "documentation.json"

#: Ce qu'un agent de documentation a le droit de toucher. Il documente ; le
#: code, les tickets et les ADR ne sont pas à lui.
_DOCUMENTABLE = ("README.md", "docs/")

#: En dessous de cette part du fichier d'origine, un remplacement n'est plus
#: une modification : c'est une amputation.
_PART_MINIMALE = 0.5


class EditionRefusee(Exception):
    """Une modification proposée ne s'applique pas. Rien n'a été écrit."""


@dataclass(frozen=True)
class TicketADocumenter:
    id: str
    titre: str
    corps: str


def _documentable(chemin: str) -> bool:
    normalise = chemin.replace("\\", "/")
    if ".." in normalise or normalise.startswith("/"):
        return False
    return any(normalise.startswith(prefixe) for prefixe in _DOCUMENTABLE)


def appliquer_editions(project_path: Path, editions: list[dict[str, object]]) -> list[str]:
    """Applique toutes les modifications, ou aucune.

    Une documentation à moitié mise à jour est pire qu'une documentation en
    retard : elle a l'air à jour.
    """
    resultat: dict[Path, str] = {}

    for edition in editions:
        chemin = str(edition.get("fichier", ""))
        if not _documentable(chemin):
            raise EditionRefusee(
                f"{chemin} n'est pas de la documentation : un agent de "
                "documentation ne touche ni au code, ni aux tickets, ni aux ADR."
            )

        fichier = project_path / chemin
        if not fichier.is_file():
            raise EditionRefusee(f"{chemin} : fichier introuvable.")

        avant = resultat.get(fichier, fichier.read_text(encoding="utf-8"))

        if "apres_section" in edition:
            resultat[fichier] = _inserer(avant, edition, chemin)
            continue

        resultat[fichier] = _remplacer(avant, edition, chemin)

    for fichier, contenu in resultat.items():
        fichier.write_text(contenu, encoding="utf-8")
    return [str(f) for f in resultat]


def _remplacer(avant: str, edition: dict[str, object], chemin: str) -> str:
    ancien = str(edition.get("ancien", ""))
    nouveau = str(edition.get("nouveau", ""))
    if not ancien:
        raise EditionRefusee(f"{chemin} : modification sans texte à remplacer.")

    occurrences = avant.count(ancien)
    if occurrences == 0:
        raise EditionRefusee(
            f"{chemin} : texte introuvable — « {ancien[:60]} ». "
            "L'agent a proposé une modification sur un texte qui n'existe pas."
        )
    if occurrences > 1:
        raise EditionRefusee(
            f"{chemin} : texte présent {occurrences} fois — on ne devine pas "
            "laquelle remplacer."
        )

    apres = avant.replace(ancien, nouveau, 1)
    if len(apres) < len(avant) * _PART_MINIMALE:
        raise EditionRefusee(
            f"{chemin} : le fichier serait amputé de plus de la moitié "
            f"({len(avant)} → {len(apres)} caractères). C'est la panne que ce "
            "contrat existe pour empêcher."
        )
    return apres


def _inserer(avant: str, edition: dict[str, object], chemin: str) -> str:
    section = str(edition.get("apres_section", ""))
    texte = str(edition.get("texte", ""))
    if section not in avant:
        raise EditionRefusee(f"{chemin} : section « {section} » introuvable.")

    lignes = avant.splitlines(keepends=True)
    debut = next(i for i, l in enumerate(lignes) if l.startswith(section))
    niveau = len(section) - len(section.lstrip("#"))
    fin = len(lignes)
    for i in range(debut + 1, len(lignes)):
        titre = lignes[i].lstrip()
        if titre.startswith("#"):
            if len(titre) - len(titre.lstrip("#")) <= niveau:
                fin = i
                break
    return "".join(lignes[:fin]) + texte.rstrip("\n") + "\n\n" + "".join(lignes[fin:])


def tickets_a_documenter(project_path: Path) -> list[TicketADocumenter]:
    """Les tickets terminés depuis la dernière mise à jour de la doc."""
    dossier = project_path / "tickets" / "done"
    if not dossier.is_dir():
        return []

    dernier = _dernier_documente(project_path)
    tickets: list[TicketADocumenter] = []
    for fichier in sorted(dossier.glob("*.md")):
        identifiant = "-".join(fichier.stem.split("-")[:2])
        if dernier is not None and identifiant <= dernier:
            continue
        tickets.append(
            TicketADocumenter(
                id=identifiant,
                titre=_titre(fichier),
                corps=fichier.read_text(encoding="utf-8"),
            )
        )
    return tickets


def _titre(fichier: Path) -> str:
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        if ligne.startswith("title:"):
            return ligne.split(":", 1)[1].strip().strip('"')
    return fichier.stem


def _dernier_documente(project_path: Path) -> str | None:
    marqueur = project_path / "memory" / _MARQUEUR
    if not marqueur.is_file():
        return None
    try:
        data = json.loads(marqueur.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Mieux vaut re-documenter que ne plus jamais documenter.
        _logger.warning("marqueur_doc_illisible", extra={"path": str(marqueur)})
        return None
    valeur = data.get("dernier_ticket")
    return str(valeur) if valeur else None


def marquer_documente(project_path: Path, ticket_id: str) -> None:
    """Retient jusqu'où la documentation est à jour."""
    memoire = project_path / "memory"
    memoire.mkdir(parents=True, exist_ok=True)
    (memoire / _MARQUEUR).write_text(
        json.dumps({"dernier_ticket": ticket_id}, indent=2) + "\n", encoding="utf-8"
    )


@dataclass(frozen=True)
class ResultatDocumentation:
    fichiers_modifies: list[str]
    refus: list[str]
    tickets: list[str]


#: Les deux lectures d'une même livraison. Deux rôles et pas un seul : un agent
#: à qui on demande les deux écrit un guide utilisateur plein de noms de
#: classes, parce que c'est ce qu'il vient de lire.
_ROLES = ("doc-technique", "doc-fonctionnelle")

_MODELE = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 4096


class DocumentationService:
    """Met à jour la documentation depuis un **lot** de tickets livrés.

    Un appel par agent et par lot, pas par ticket : dix tickets documentés un
    par un coûteraient vingt appels et réécriraient le même fichier dix fois
    pour une même feature.
    """

    def __init__(self, provider: LLMProvider, prompts_dir: Path) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir

    async def mettre_a_jour(self, project_path: Path) -> ResultatDocumentation:
        tickets = tickets_a_documenter(project_path)
        if not tickets:
            # Un lot vide ne coûte rien : c'est ce qui permet de brancher la
            # mise à jour sur la fin de chaque file sans la payer à chaque fois.
            return ResultatDocumentation([], [], [])

        modifies: list[str] = []
        refus: list[str] = []
        brief = _brief(tickets)

        for role in _ROLES:
            systeme = (self._prompts_dir / f"{role}.md").read_text(encoding="utf-8")
            reponse = await self._provider.complete(
                system=systeme,
                user=brief,
                model=_MODELE,
                max_tokens=_MAX_TOKENS,
            )
            editions = _editions_de(str(reponse.content), role)
            if not editions:
                continue
            try:
                modifies.extend(appliquer_editions(project_path, editions))
            except EditionRefusee as exc:
                # Un agent qui se trompe n'empêche pas l'autre d'avoir raison.
                _logger.warning("editions_refusees", extra={"role": role})
                refus.append(f"{role} : {exc}")

        marquer_documente(project_path, tickets[-1].id)
        return ResultatDocumentation(
            fichiers_modifies=modifies,
            refus=refus,
            tickets=[t.id for t in tickets],
        )


def _brief(tickets: list[TicketADocumenter]) -> str:
    """Ce que les agents reçoivent : les tickets, pas les diffs.

    Un diff dit ce qui a bougé ligne à ligne ; un ticket dit ce que le produit
    fait de plus. C'est la seconde chose qu'on documente, et elle tient en
    dix fois moins de tokens.
    """
    morceaux = [
        "Tickets livrés depuis la dernière mise à jour de la documentation :",
        "",
    ]
    for ticket in tickets:
        morceaux.append(f"## {ticket.id} — {ticket.titre}\n\n{ticket.corps}\n")
    return "\n".join(morceaux)


def _editions_de(contenu: str, role: str) -> list[dict[str, object]]:
    """Lit le JSON de l'agent. Une réponse illisible ne fait rien écrire."""
    texte = contenu.strip()
    if "```" in texte:
        morceaux = texte.split("```")
        texte = next(
            (m[4:] if m.startswith("json") else m for m in morceaux if "{" in m), texte
        )
    try:
        data = json.loads(texte[texte.index("{") : texte.rindex("}") + 1])
    except (json.JSONDecodeError, ValueError):
        _logger.warning("reponse_doc_illisible", extra={"role": role})
        return []
    editions = data.get("editions", [])
    return list(editions) if isinstance(editions, list) else []
