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
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services import documentation_claude_md as claude_md_doc
from tessera.services.documentation_code import (
    FournisseurMatiere,
    MatiereCode,
    bloc_diffs,
    bloc_fichiers,
    matiere_du_lot,
)
from tessera.services.providers.base import LLMProvider
from tessera.services.modeles_par_defaut import MODELE_PRODUCTION
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
#: on garde les N plus anciens (les plus petits identifiants) et l'événement
#: le signale : les autres restent hors du marqueur et ouvrent le lot suivant.
#: Un lot démesuré épuise le contexte du provider, et chaque ticket y apporte
#: son diff (ticket-541) ; garder les plus récents laissait un trou dans
#: l'historique documenté que personne ne rattrapait.
_PLAFOND = 5

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

    Une édition ``contenu`` crée un fichier absent (ticket-342) : sans elle, un
    guide qui n'existe pas encore ne pouvait jamais naître. Elle n'écrase
    jamais un fichier existant.
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

        if "contenu" in edition:
            if fichier in resultat or fichier.exists():
                raise EditionRefusee(
                    f"{chemin} existe déjà : `contenu` ne sert qu'à créer un fichier "
                    "absent. Modifier un fichier passe par `ancien` ou `apres_section`."
                )
            contenu = str(edition.get("contenu", ""))
            if not contenu.strip():
                raise EditionRefusee(f"{chemin} : création sans contenu.")
            resultat[fichier] = contenu
            continue

        if fichier not in resultat and not fichier.is_file():
            raise EditionRefusee(
                f"{chemin} : fichier introuvable. Pour le créer, donner son texte "
                "entier dans `contenu`."
            )

        # Pas de `resultat.get(fichier, read_text())` : le défaut serait lu sur
        # disque même pour un fichier que ce lot vient de créer.
        avant = resultat[fichier] if fichier in resultat else fichier.read_text(encoding="utf-8")

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
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(contenu, encoding="utf-8")
    return [str(f) for f in resultat]


def _remplacer(avant: str, edition: dict[str, object], chemin: str) -> str:
    ancien = str(edition.get("ancien", ""))
    nouveau = str(edition.get("nouveau", ""))
    if not ancien:
        raise EditionRefusee(f"{chemin} : modification sans texte à remplacer.")

    debut, fin = _localiser(avant, ancien, chemin)
    apres = avant[:debut] + nouveau + avant[fin:]
    if len(apres) < len(avant) * _PART_MINIMALE:
        raise EditionRefusee(
            f"{chemin} : le fichier serait amputé de plus de la moitié "
            f"({len(avant)} → {len(apres)} caractères). C'est la panne que ce "
            "contrat existe pour empêcher."
        )
    return apres


#: Typographie française ramenée à son équivalent ASCII (ticket-402). Chaque
#: caractère devient exactement un caractère : les positions se correspondent.
_TYPO = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "«": '"',
        "»": '"',
        " ": " ",
        " ": " ",
    }
)


def _normaliser_typo(texte: str) -> tuple[str, list[int]]:
    """Normalize typographic punctuation and non-breaking spaces.

    Returns the normalized text and, for each of its characters, the position
    of the originating character in ``texte``. The ellipsis is the only
    character that expands to three, hence the position map.
    """
    sortie: list[str] = []
    positions: list[int] = []
    for i, c in enumerate(texte):
        rendu = "..." if c == "…" else c.translate(_TYPO)
        sortie.append(rendu)
        positions.extend([i] * len(rendu))
    return "".join(sortie), positions


def _positions_de(texte: str, motif: str) -> list[int]:
    """Start offsets of every non-overlapping occurrence of ``motif``."""
    trouvees: list[int] = []
    debut = texte.find(motif)
    while debut != -1:
        trouvees.append(debut)
        debut = texte.find(motif, debut + len(motif))
    return trouvees


def _localiser(avant: str, ancien: str, chemin: str) -> tuple[int, int]:
    """Locate ``ancien`` in ``avant`` and return its (start, end) offsets.

    An exact match wins. Otherwise the search is retried after normalizing
    typography on both sides, and the offsets are mapped back to ``avant`` so
    the rest of the file keeps its typography.
    """
    exactes = _positions_de(avant, ancien)
    if len(exactes) == 1:
        return exactes[0], exactes[0] + len(ancien)

    if len(exactes) == 0:
        norm_avant, pos_avant = _normaliser_typo(avant)
        norm_ancien, _ = _normaliser_typo(ancien)
        trouvees = _positions_de(norm_avant, norm_ancien) if norm_ancien else []
        if len(trouvees) == 1:
            debut = trouvees[0]
            dernier = pos_avant[debut + len(norm_ancien) - 1]
            return pos_avant[debut], dernier + 1
        exactes = trouvees

    if not exactes:
        raise EditionRefusee(
            f"{chemin} : texte introuvable — « {ancien[:60]} ». "
            "L'agent a proposé une modification sur un texte qui n'existe pas."
        )
    raise EditionRefusee(
        f"{chemin} : texte présent {len(exactes)} fois — on ne devine pas "
        "laquelle remplacer."
    )


def _normaliser_section(texte: str) -> str:
    """Normalize a section title for case-, whitespace- and typography-tolerant comparison.

    Collapses multiple spaces, strips leading/trailing whitespace, lowercases
    and flattens typographic punctuation (ticket-402).
    Applied to both the requested section and each candidate heading line.
    """
    plat, _ = _normaliser_typo(texte)
    return re.sub(r"\s+", " ", plat.strip()).lower()


def _inserer(avant: str, edition: dict[str, object], chemin: str) -> str:
    """Insert text after a Markdown section, with tolerant anchor matching.

    The section is matched after normalizing casse and extra whitespace (ticket-395).
    A unique match at the exact heading level is required; zero or two+ matches → refused.
    """
    section = str(edition.get("apres_section", ""))
    texte = str(edition.get("texte", ""))

    niveau = len(section) - len(section.lstrip("#"))
    prefixe = "#" * niveau + " "
    section_norm = _normaliser_section(section)

    lignes = avant.splitlines(keepends=True)
    # Candidats : lignes qui démarrent au bon niveau de titre et correspondent
    # après normalisation (casse et espaces multiples tolérés).
    candidats = [
        i
        for i, l in enumerate(lignes)
        if l.startswith(prefixe) and _normaliser_section(l.rstrip()) == section_norm
    ]

    if len(candidats) == 0:
        raise EditionRefusee(f"{chemin} : section « {section} » introuvable.")
    if len(candidats) > 1:
        raise EditionRefusee(
            f"{chemin} : section « {section} » correspond à {len(candidats)} titres "
            "après normalisation — titre ambigu."
        )

    debut = candidats[0]
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
    ) -> None:
        self._provider = provider
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

        for role in self._roles:
            systeme = (self._prompts_dir / f"{role}.md").read_text(encoding="utf-8")
            provider, modele = self._pour(role)
            # Seul `doc-technique` voit le CLAUDE.md, et seul lui peut l'éditer.
            claude_md = self._claude_md if role == claude_md_doc.ROLE else None
            user = brief + claude_md_doc.section_du_brief(claude_md)
            reponse = await provider.complete(
                system=systeme,
                user=user,
                model=modele,
                max_tokens=_MAX_TOKENS,
            )
            editions = _editions_de(str(reponse.content), role)
            if not editions:
                continue
            try:
                modifies.extend(appliquer_editions(racine, editions, claude_md=claude_md))
            except EditionRefusee as exc:
                # Tour de correction (ticket-395) : rappeler l'agent une seule fois
                # avec le motif du refus et les titres des fichiers visés.
                tour_de_correction = True
                motif = str(exc)
                titres = _titres_fichiers_vises(racine, editions)
                reponse2 = await provider.complete(
                    system=systeme,
                    user=_brief_correction(user, str(reponse.content), motif, titres),
                    model=modele,
                    max_tokens=_MAX_TOKENS,
                )
                editions2 = _editions_de(str(reponse2.content), role)
                if not editions2:
                    continue
                try:
                    modifies.extend(appliquer_editions(racine, editions2, claude_md=claude_md))
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
            fichiers_modifies=modifies,
            refus=refus,
            tickets=[t.id for t in tickets],
            tronque=tronque,
            marqueur_ecrit=marqueur_ecrit,
            tour_de_correction=tour_de_correction,
            ecartes=ecartes,
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
) -> str:
    """Message for the one-shot corrective round (ticket-395)."""
    parties: list[str] = [
        user_original,
        "\n\n---\n\nTa réponse précédente a été refusée.\n\n"
        f"Motif du refus : {motif_refus}",
    ]
    if titres_fichiers:
        parties.append(
            "\n\nTitres Markdown des fichiers visés (liste exhaustive) :" + titres_fichiers
        )
    parties.append("\n\nPropose une nouvelle liste d'éditions corrigée.")
    return "".join(parties)


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
