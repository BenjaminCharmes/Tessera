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

**Le troisième était le rattrapage initial.** Sans marqueur, tous les tickets
terminés partaient en un seul lot — des centaines de tickets sur un projet
mature, soit un prompt de plusieurs centaines de milliers de tokens. La
première mise à jour détecte l'absence de marqueur, l'initialise avec tous
les tickets existants, et ne documente rien — le rattrapage d'un coup
coûterait plus qu'il n'apporterait.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services import documentation_claude_md as claude_md_doc
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

#: Nombre maximum de tickets traités en un seul lot (ticket-213). Au-delà,
#: on garde les N plus récents (les plus grands identifiants) et l'événement
#: le signale — un lot démesuré épuise le contexte du provider avant même
#: que le premier agent ait commencé à réfléchir.
_PLAFOND = 10

#: Volume total de documentation inclus dans le message (en caractères).
#: Au-delà, un fichier est représenté par ses seuls titres Markdown.
_BORNE_DOC = 60_000


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


def appliquer_editions(
    racine: Path, editions: list[dict[str, object]], claude_md: Path | None = None
) -> list[str]:
    """Applique toutes les modifications, ou aucune.

    Une documentation à moitié mise à jour est pire qu'une documentation en
    retard : elle a l'air à jour.

    ``claude_md`` est le CLAUDE.md du projet quand il le déclare documentable
    (ticket-244) ; sans lui, une modification de « CLAUDE.md » est refusée.
    """
    resultat: dict[Path, str] = {}

    for edition in editions:
        chemin = str(edition.get("fichier", ""))
        if chemin == claude_md_doc.NOM and claude_md is not None:
            fichier = claude_md
        elif not _documentable(chemin):
            raise EditionRefusee(
                f"{chemin} n'est pas de la documentation : un agent de "
                "documentation ne touche ni au code, ni aux tickets, ni aux ADR."
            )
        else:
            fichier = racine / chemin
        if not fichier.is_file():
            raise EditionRefusee(f"{chemin} : fichier introuvable.")

        avant = resultat.get(fichier, fichier.read_text(encoding="utf-8"))

        if "apres_section" in edition:
            resultat[fichier] = _inserer(avant, edition, chemin)
            continue

        resultat[fichier] = _remplacer(avant, edition, chemin)

    if claude_md is not None and claude_md in resultat:
        refus = claude_md_doc.depasse_le_budget(
            claude_md.read_text(encoding="utf-8"), resultat[claude_md]
        )
        if refus is not None:
            raise EditionRefusee(refus)

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


def _tickets_documentes(project_path: Path) -> set[str]:
    """Return the set of ticket IDs that have already been documented.

    Reads the new format ``{"documentes": [...]}`` and falls back to the
    legacy ``{"dernier_ticket": "..."}`` for backward compatibility (ADR-036).
    A missing or unreadable marker returns an empty set.
    """
    marqueur = project_path / "memory" / _MARQUEUR
    if not marqueur.is_file():
        return set()
    try:
        data = json.loads(marqueur.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _logger.warning("marqueur_doc_illisible", extra={"path": str(marqueur)})
        return set()

    # New format: {"documentes": ["ticket-001", ...]}
    if "documentes" in data:
        valeur = data["documentes"]
        return set(valeur) if isinstance(valeur, list) else set()

    # Old format: {"dernier_ticket": "ticket-NNN"}  (ADR-036 — lu, jamais réécrit)
    dernier = data.get("dernier_ticket")
    if not dernier:
        return set()
    dossier = project_path / "tickets" / "done"
    if not dossier.is_dir():
        return set()
    documentes: set[str] = set()
    for fichier in dossier.glob("*.md"):
        identifiant = "-".join(fichier.stem.split("-")[:2])
        if identifiant <= str(dernier):
            documentes.add(identifiant)
    return documentes


def tickets_a_documenter(project_path: Path) -> list[TicketADocumenter]:
    """Les tickets terminés qui ne figurent pas encore dans le marqueur.

    Filtre par ensemble d'identifiants documentés plutôt que par comparaison
    de chaînes : un ticket livré avec un identifiant inférieur au dernier
    documenté (livraison hors ordre) est inclus, là où l'ancien filtre
    ``identifiant <= dernier`` l'aurait exclu définitivement.
    """
    dossier = project_path / "tickets" / "done"
    if not dossier.is_dir():
        return []

    documentes = _tickets_documentes(project_path)
    tickets: list[TicketADocumenter] = []
    for fichier in sorted(dossier.glob("*.md")):
        identifiant = "-".join(fichier.stem.split("-")[:2])
        if identifiant in documentes:
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


def marquer_documente(project_path: Path, ticket_ids: list[str]) -> None:
    """Record which ticket IDs have been documented.

    Merges ``ticket_ids`` with any already-documented IDs and writes the new
    ``{"documentes": [...]}`` format.  The old ``{"dernier_ticket": ...}``
    format is never written back (ADR-036).
    """
    existants = _tickets_documentes(project_path)
    tous = existants | set(ticket_ids)
    memoire = project_path / "memory"
    memoire.mkdir(parents=True, exist_ok=True)
    (memoire / _MARQUEUR).write_text(
        json.dumps({"documentes": sorted(tous)}, indent=2) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class ResultatDocumentation:
    fichiers_modifies: list[str]
    refus: list[str]
    tickets: list[str]
    #: True si le lot a été tronqué à ``_PLAFOND`` tickets (ticket-213).
    tronque: bool = False
    #: True si le marqueur a été écrit (initialisation ou avancement). Permet
    #: à ``_documenter_le_run`` de commiter le marqueur même quand aucun
    #: fichier de doc n'a changé, pour garder l'arbre propre (ticket-213).
    marqueur_ecrit: bool = False


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

    def __init__(
        self,
        provider: LLMProvider,
        prompts_dir: Path,
        fournisseur: "Callable[[str], tuple[LLMProvider, str | None]] | None" = None,
        claude_md: Path | None = None,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        # Le CLAUDE.md du projet, s'il le déclare documentable (ticket-244).
        self._claude_md = claude_md
        # Deux rôles, donc potentiellement deux providers et deux modèles
        # (ticket-188) : `fournisseur(role)` rend la paire de chacun, le
        # modèle pouvant être None. Sans lui, le provider reçu et le modèle
        # d'avant servent aux deux.
        self._fournisseur = fournisseur

    def _pour(self, role: str) -> "tuple[LLMProvider, str]":
        if self._fournisseur is None:
            return self._provider, _MODELE
        provider, modele = self._fournisseur(role)
        return provider, modele or _MODELE

    async def mettre_a_jour(
        self, project_path: Path, racine_doc: Path | None = None
    ) -> ResultatDocumentation:
        """Documents the tickets delivered since the marker.

        ``racine_doc`` est le dossier où vivent ``README.md`` et ``docs/`` : le
        projet lui-même, ou le dépôt qui le contient quand il déclare
        ``git_root: ancestor`` — le projet bootstrap documente l'IDE à la racine
        du dépôt, pas sous ``projects/ide-core/`` (ticket-198). Les tickets et
        le marqueur, eux, restent ceux du projet.

        Quand le marqueur n'existe pas, le service l'initialise avec tous les
        tickets terminés existants et rend un résultat vide : on ne rattrape pas
        des centaines de tickets d'un coup sur un projet mature (ticket-213).
        """
        racine = racine_doc or project_path
        marqueur = project_path / "memory" / _MARQUEUR

        # Sans marqueur : initialiser et ne rien documenter (ticket-213).
        if not marqueur.is_file():
            tous = tickets_a_documenter(project_path)
            if tous:
                marquer_documente(project_path, [t.id for t in tous])
                return ResultatDocumentation([], [], [], marqueur_ecrit=True)
            return ResultatDocumentation([], [], [])

        tickets = tickets_a_documenter(project_path)
        if not tickets:
            return ResultatDocumentation([], [], [])

        # Plafond : on ne garde que les N plus récents (ticket-213).
        tronque = len(tickets) > _PLAFOND
        if tronque:
            tickets = tickets[-_PLAFOND:]

        modifies: list[str] = []
        refus: list[str] = []
        brief = _brief(tickets, _contenu_documentable(racine))

        for role in _ROLES:
            systeme = (self._prompts_dir / f"{role}.md").read_text(encoding="utf-8")
            provider, modele = self._pour(role)
            # Seul `doc-technique` voit le CLAUDE.md, et seul lui peut l'éditer.
            claude_md = self._claude_md if role == claude_md_doc.ROLE else None
            reponse = await provider.complete(
                system=systeme,
                user=brief + claude_md_doc.section_du_brief(claude_md),
                model=modele,
                max_tokens=_MAX_TOKENS,
            )
            editions = _editions_de(str(reponse.content), role)
            if not editions:
                continue
            try:
                modifies.extend(appliquer_editions(racine, editions, claude_md=claude_md))
            except EditionRefusee as exc:
                # Un agent qui se trompe n'empêche pas l'autre d'avoir raison.
                _logger.warning("editions_refusees", extra={"role": role})
                refus.append(f"{role} : {exc}")

        # Le marqueur n'avance que si au moins une édition a été appliquée, ou
        # si aucune édition n'a été proposée. S'il n'y a que des refus, on
        # réessaiera au prochain run (ticket-213).
        toutes_refusees = not modifies and bool(refus)
        marqueur_ecrit = False
        if not toutes_refusees:
            marquer_documente(project_path, [t.id for t in tickets])
            marqueur_ecrit = True

        return ResultatDocumentation(
            fichiers_modifies=modifies,
            refus=refus,
            tickets=[t.id for t in tickets],
            tronque=tronque,
            marqueur_ecrit=marqueur_ecrit,
        )


def _titres_markdown(contenu: str) -> str:
    """Extracts Markdown heading lines (starting with #) from file content."""
    return "\n".join(l for l in contenu.splitlines() if l.startswith("#"))


def _contenu_documentable(racine: Path, borne: int = _BORNE_DOC) -> str:
    """Current content of documentable files, bounded to `borne` characters total.

    Files are included in full up to the budget. When a file would push the
    running total over ``borne``, its full content is replaced by a list of
    Markdown headings so the agents can still see the structure.
    """
    fichiers: list[tuple[str, str]] = []

    readme = racine / "README.md"
    if readme.is_file():
        fichiers.append(("README.md", readme.read_text(encoding="utf-8")))

    docs_dir = racine / "docs"
    if docs_dir.is_dir():
        for f in sorted(docs_dir.glob("*.md")):
            fichiers.append((f"docs/{f.name}", f.read_text(encoding="utf-8")))

    if not fichiers:
        return ""

    morceaux: list[str] = []
    budget = borne

    for chemin, contenu in fichiers:
        entete = f"\n### {chemin}\n\n"
        if len(entete) + len(contenu) <= budget:
            morceaux.append(entete + contenu)
            budget -= len(entete) + len(contenu)
        else:
            titres = _titres_markdown(contenu)
            resume = entete + f"[contenu trop long — titres uniquement]\n{titres}\n"
            morceaux.append(resume)
            budget -= len(resume)
            if budget <= 0:
                break

    if not morceaux:
        return ""
    return "\n---\nDocumentation actuelle :\n" + "".join(morceaux)


def _brief(tickets: list[TicketADocumenter], contenu_doc: str = "") -> str:
    """Ce que les agents reçoivent : les tickets, puis la documentation actuelle.

    Un diff dit ce qui a bougé ligne à ligne ; un ticket dit ce que le produit
    fait de plus. C'est la seconde chose qu'on documente, et elle tient en
    dix fois moins de tokens.  La documentation actuelle permet à l'agent de
    copier mot pour mot l'ancien texte qu'il souhaite remplacer.
    """
    morceaux = [
        "Tickets livrés depuis la dernière mise à jour de la documentation :",
        "",
    ]
    for ticket in tickets:
        morceaux.append(f"## {ticket.id} — {ticket.titre}\n\n{ticket.corps}\n")
    if contenu_doc:
        morceaux.append(contenu_doc)
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
