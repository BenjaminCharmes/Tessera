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
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.documentation import documentation_claude_md as claude_md_doc
from tessera.services.documentation.documentation_base import EditionRefusee, _titres_markdown
from tessera.services.documentation.documentation_code import FournisseurMatiere, MatiereCode, bloc_diffs, bloc_fichiers, matiere_du_lot
from tessera.services.documentation.documentation_description import appliquer_description
from tessera.services.documentation.documentation_editions import _documentable, appliquer_editions
from tessera.services.documentation.documentation_preuve import fichiers_de_la_matiere
from tessera.services.documentation.documentation_reponse import donnees_de, editions_de, editions_depuis
from tessera.services.documentation.documentation_selection import MARQUEUR, TicketADocumenter, marquer_documente, tickets_a_documenter
from tessera.services.noyau.modeles_par_defaut import MODELE_PRODUCTION
from tessera.services.providers.base import LLMProvider
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Nombre maximum de tickets traités en un seul lot (ticket-213). Au-delà,
#: on garde les N plus anciens (les plus petits identifiants) et l'événement
#: le signale : les autres restent hors du marqueur et ouvrent le lot suivant.
#: Un lot démesuré épuise le contexte du provider, et chaque ticket y apporte
#: son diff (ticket-541) ; garder les plus récents laissait un trou dans
#: l'historique documenté que personne ne rattrapait.
_PLAFOND = 5

#: Volume total de documentation inclus dans le message (en caractères).
#: Au-delà, un fichier est représenté par ses seuls titres Markdown.
_BORNE_DOC = 60_000


@dataclass(frozen=True)
class ResultatDocumentation:
    fichiers_modifies: list[str]
    refus: list[str]
    tickets: list[str]
    #: True si le lot a été tronqué à ``_PLAFOND`` tickets (ticket-213).
    tronque: bool = False
    #: True si le marqueur a été écrit (initialisation ou avancement). Permet
    #: à ``documenter_le_run`` de commiter le marqueur même quand aucun
    #: fichier de doc n'a changé, pour garder l'arbre propre (ticket-213).
    marqueur_ecrit: bool = False
    #: True si au moins un agent a nécessité un tour de correction (ticket-395).
    tour_de_correction: bool = False
    #: Tickets retirés du lot faute de diff retrouvable : marqués documentés,
    #: jamais lus par un agent (ticket-541).
    ecartes: list[str] = field(default_factory=list)


#: Les deux lectures d'une même livraison. Deux rôles et pas un seul : un agent
#: à qui on demande les deux écrit un guide utilisateur plein de noms de
#: classes, parce que c'est ce qu'il vient de lire.
_ROLES = ("doc-technique", "doc-fonctionnelle")
ROLES_DOCUMENTATION = _ROLES

_MODELE = MODELE_PRODUCTION
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
        roles: tuple[str, ...] = _ROLES,
        base: str | None = None,
        matiere: FournisseurMatiere | None = None,
        phrases_interdites: list[str] | None = None,
    ) -> None:
        self._provider = provider
        self._phrases_interdites = phrases_interdites or []  # ticket-936
        # La base déclarée du projet et la source de la matière de code : le
        # diff de chaque ticket se prend contre elle (ticket-541).
        self._base = base
        self._matiere = matiere
        # Les rôles à appeler : l'appelant filtre ceux que le projet coupe
        # (ticket-534). Vide, le service ne fait rien.
        self._roles = roles
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
        # Aucun rôle actif : ni appel, ni marqueur — le projet a coupé la doc,
        # et la rallumer doit rattraper ce qui s'est livré entre-temps.
        if not self._roles:
            return ResultatDocumentation([], [], [])

        racine = racine_doc or project_path
        marqueur = project_path / "memory" / MARQUEUR

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

        # Plafond : on garde les N plus anciens ; les autres ouvrent le lot
        # suivant, le marqueur ne les ayant pas vus (ticket-541).
        tronque = len(tickets) > _PLAFOND
        tickets = tickets[:_PLAFOND]

        fournir = self._matiere or matiere_du_lot
        matiere = await fournir(
            racine, project_path, [t.id for t in tickets], self._base
        )
        ecartes = matiere.sans_diff
        if ecartes:
            # Sans diff, rien à documenter : le ticket ne reviendra pas dans
            # le lot suivant. L'orchestrateur en journalise chaque ligne.
            marquer_documente(project_path, ecartes)
            tickets = [t for t in tickets if t.id not in ecartes]
        if not tickets:
            return ResultatDocumentation(
                [], [], [], tronque=tronque, marqueur_ecrit=True, ecartes=ecartes
            )

        modifies: list[str] = []
        refus: list[str] = []
        tour_de_correction = False
        brief = _brief(tickets, matiere, _contenu_documentable(racine))
        # Le texte des tickets sert au contrôle des jetons : un numéro d'ADR
        # qu'un ticket cite n'est pas inventé (ticket-542).
        intentions = "\n".join(f"{t.titre}\n{t.corps}" for t in tickets)
        fichiers = fichiers_de_la_matiere(matiere)
        # La description se compte à part : elle ne décide pas du marqueur (ticket-724).
        fichiers_description: list[str] = []
        refus_description: list[str] = []

        for role in self._roles:
            systeme = (self._prompts_dir / f"{role}.md").read_text(encoding="utf-8")
            provider, modele = self._pour(role)
            # Seul `doc-technique` voit le CLAUDE.md et l'AGENTS.md, et seul lui
            # peut les éditer ou proposer la description (ticket-244, 724).
            technique = role == claude_md_doc.ROLE
            claude_md = self._claude_md if technique else None
            agents_md = claude_md_doc.agents_md_de(racine, claude_md)
            user = brief + claude_md_doc.sections_du_brief(claude_md, agents_md)
            reponse = await provider.complete(
                system=systeme,
                user=user,
                model=modele,
                max_tokens=_MAX_TOKENS,
                cwd=project_path,
            )
            donnees = donnees_de(str(reponse.content), role)
            if technique:
                # L'agents.json du dossier où le run écrit, jamais le checkout.
                ecrits, refuses = appliquer_description(
                    project_path / "agents.json", donnees, matiere, intentions, role,
                    self._phrases_interdites,
                )
                fichiers_description.extend(ecrits)
                refus_description.extend(refuses)
            editions = editions_depuis(donnees)
            if not editions:
                continue
            try:
                modifies.extend(
                    appliquer_editions(racine, editions, claude_md, matiere, intentions, agents_md)
                )
            except EditionRefusee as exc:
                # Tour de correction (ticket-395) : rappeler l'agent une seule fois
                # avec le motif du refus et les titres des fichiers visés.
                tour_de_correction = True
                motif = str(exc)
                titres = _titres_fichiers_vises(racine, editions)
                reponse2 = await provider.complete(
                    system=systeme,
                    user=_brief_correction(
                        user, str(reponse.content), motif, titres, fichiers
                    ),
                    model=modele,
                    max_tokens=_MAX_TOKENS,
                    cwd=project_path,
                )
                editions2 = editions_de(str(reponse2.content), role)
                if not editions2:
                    continue
                try:
                    modifies.extend(
                        appliquer_editions(
                            racine, editions2, claude_md, matiere, intentions, agents_md
                        )
                    )
                except EditionRefusee as exc2:
                    # Deuxième refus : comportement courant (ticket-395).
                    _logger.warning(
                        "editions_refusees", extra={"role": role, "motif": str(exc2)}
                    )
                    refus.append(f"{role} : {exc2}")

        # Le marqueur n'avance que si au moins une édition a été appliquée, ou
        # si aucune édition n'a été proposée. S'il n'y a que des refus, on
        # réessaiera au prochain run (ticket-213).
        toutes_refusees = not modifies and bool(refus)
        marqueur_ecrit = bool(ecartes)
        if not toutes_refusees:
            marquer_documente(project_path, [t.id for t in tickets])
            marqueur_ecrit = True

        return ResultatDocumentation(
            fichiers_modifies=[*modifies, *fichiers_description],
            refus=[*refus, *refus_description],
            tickets=[t.id for t in tickets],
            tronque=tronque,
            marqueur_ecrit=marqueur_ecrit,
            tour_de_correction=tour_de_correction,
            ecartes=ecartes,
        )


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


def _brief(
    tickets: list[TicketADocumenter], matiere: MatiereCode, contenu_doc: str = ""
) -> str:
    """Ce que les agents reçoivent, dans cet ordre : quatre blocs.

    1. les tickets (l'intention) ; 2. le diff livré de chaque ticket ;
    3. le contenu actuel des fichiers que ces diffs touchent ; 4. la
    documentation actuelle, que l'agent recopie mot pour mot pour remplacer un
    texte. Un ticket dit ce qu'on voulait, le code dit ce qui existe : un
    nombre ou un nom absent des deux blocs de code n'est pas à écrire
    (ADR-057).
    """
    morceaux = [
        "Tickets livrés depuis la dernière mise à jour de la documentation :",
        "",
    ]
    for ticket in tickets:
        morceaux.append(f"## {ticket.id} — {ticket.titre}\n\n{ticket.corps}\n")
    suite = (bloc_diffs(matiere), bloc_fichiers(matiere), contenu_doc)
    morceaux.extend(bloc for bloc in suite if bloc)
    return "\n".join(morceaux)


def _titres_fichiers_vises(racine: Path, editions: list[dict[str, object]]) -> str:
    """Get Markdown headings of files targeted by the editions.

    Returns a formatted string listing headings per file, to be included in the
    corrective-round message so the agent can pick a valid existing section.
    """
    morceaux: list[str] = []
    vus: set[str] = set()
    for ed in editions:
        chemin = str(ed.get("fichier", ""))
        if chemin in vus:
            continue
        vus.add(chemin)
        # `fichier` vient de la réponse de l'agent : seule la documentation se
        # lit, comme seule elle s'écrit (`appliquer_editions`), et jamais hors
        # de la racine — un « ../../.env » ne doit rien renvoyer au modèle.
        if not _documentable(chemin):
            continue
        fichier = (racine / chemin).resolve()
        if not fichier.is_relative_to(racine.resolve()):
            continue
        if fichier.is_file():
            titres = _titres_markdown(fichier.read_text(encoding="utf-8"))
            if titres:
                morceaux.append(f"\n### {chemin}\n\n{titres}")
    return "".join(morceaux)


def _brief_correction(
    user_original: str,
    reponse_precedente: str,
    motif_refus: str,
    titres_fichiers: str,
    fichiers_matiere: list[str] | None = None,
) -> str:
    """Message for the one-shot corrective round (ticket-395).

    ``fichiers_matiere`` lists the files the agent was given: a ``preuve`` can
    only cite one of them (ticket-542).
    """
    parties: list[str] = [
        user_original,
        "\n\n---\n\nTa réponse précédente a été refusée.\n\n"
        f"Motif du refus : {motif_refus}",
    ]
    if titres_fichiers:
        parties.append(
            "\n\nTitres Markdown des fichiers visés (liste exhaustive) :" + titres_fichiers
        )
    if fichiers_matiere:
        parties.append(
            "\n\nFichiers du code fourni, où une preuve peut puiser : "
            + ", ".join(fichiers_matiere)
        )
    parties.append("\n\nPropose une nouvelle liste d'éditions corrigée.")
    return "".join(parties)
