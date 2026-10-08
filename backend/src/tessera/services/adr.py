"""N'injecter à chaque agent que les contraintes qui le concernent.

`contraintes.md` remplace `decisions.md` dans le prompt des agents (ticket-311).
Il porte des règles concises, filtrées par rôle via des marqueurs `*(role)*`.
Si `contraintes.md` est absent, on retombe sur `decisions.md` (ticket-087).

Dans `decisions.md`, la portée s'exprime via `**Portée** : rôle` dans chaque
bloc ADR. Dans `contraintes.md`, des marqueurs `*(role1, role2)*` sur leur
propre ligne ouvrent un bloc scoped ; les règles sans marqueur vont à tous.

**Sans portée, une contrainte vaut pour tous** — le défaut protège.
"""
import re
from dataclasses import dataclass
from pathlib import Path

#: `## ADR-0xx — Titre` ouvre un bloc ; le suivant le ferme.
_DEBUT_ADR = re.compile(r"^##\s+(ADR-\d+)\b", re.MULTILINE)

#: `**Portée** : a, b` — la ligne, où qu'elle soit dans le bloc.
_PORTEE = re.compile(r"^\*\*Port[ée]e\*\*\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)

#: `*(role1, role2)*` seul sur sa ligne — marqueur de portée dans contraintes.md.
_MARQUEUR_ROLE = re.compile(r"^\*\(([^)]+)\)\*$")


@dataclass(frozen=True)
class BlocADR:
    numero: str
    texte: str


def decouper(contenu: str) -> list[BlocADR]:
    """Découpe `decisions.md` en un bloc par ADR, préambule exclu."""
    debuts = list(_DEBUT_ADR.finditer(contenu))
    blocs: list[BlocADR] = []
    for index, debut in enumerate(debuts):
        fin = debuts[index + 1].start() if index + 1 < len(debuts) else len(contenu)
        blocs.append(
            BlocADR(numero=debut.group(1), texte=contenu[debut.start() : fin].rstrip())
        )
    return blocs


def portee_de(bloc: BlocADR) -> set[str] | None:
    """Les rôles que cet ADR contraint, ou `None` s'il les contraint tous."""
    trouve = _PORTEE.search(bloc.texte)
    if trouve is None:
        return None
    roles = {r.strip().lower() for r in trouve.group(1).split(",") if r.strip()}
    if not roles or "tous" in roles:
        return None
    return roles


def preambule(contenu: str) -> str:
    """Ce qui précède le premier ADR : titre et format du fichier."""
    premier = _DEBUT_ADR.search(contenu)
    return contenu[: premier.start()] if premier else contenu


def adr_pour(contenu: str, role: str) -> str:
    """Le fichier de décisions réduit à ce qui contraint `role`.

    Un ADR sans portée passe toujours ; un ADR avec portée ne passe qu'aux
    rôles qu'il nomme.

    Ce qui rend la règle sûre est **ce qu'on annote**. Une portée se déclare
    sur un ADR qui enregistre un choix passé — pourquoi `uv`, pourquoi Tauri,
    comment `ProjectLoader` est structuré. Les contraintes de comportement —
    git, artefacts, périmètre d'écriture — n'en portent pas, donc elles vont
    à tout le monde, y compris à un agent que l'utilisateur vient de créer et
    que personne n'avait prévu.
    """
    if not contenu.strip():
        return contenu

    cible = role.strip().lower()
    retenus = [
        bloc.texte
        for bloc in decouper(contenu)
        if (p := portee_de(bloc)) is None or cible in p
    ]
    if not retenus:
        return preambule(contenu).rstrip() + "\n"
    return preambule(contenu).rstrip() + "\n\n" + "\n\n---\n\n".join(retenus) + "\n"


def contraintes_pour(contenu: str, role: str) -> str:
    """Filtre contraintes.md : garde les règles universelles et celles de `role`.

    Un marqueur `*(role1, role2)*` seul sur sa ligne ouvre un bloc scoped qui
    court jusqu'à la prochaine section `## Header` ou au prochain marqueur.
    Les règles sans marqueur précédent sont universelles et vont à tous les rôles.
    Le marqueur lui-même n'apparaît pas dans la sortie.
    """
    if not contenu.strip():
        return contenu

    cible = role.strip().lower()
    lignes = contenu.splitlines(keepends=True)
    result: list[str] = []
    portee_courante: set[str] | None = None  # None = universel

    for ligne in lignes:
        stripped = ligne.strip()

        # Marqueur de rôle : met à jour la portée sans s'inclure dans la sortie.
        m = _MARQUEUR_ROLE.match(stripped)
        if m:
            roles = {r.strip().lower() for r in m.group(1).split(",") if r.strip()}
            portee_courante = roles if roles else None
            continue

        # Un en-tête de section `## Header` réinitialise la portée (universel).
        if stripped.startswith("## "):
            portee_courante = None
            result.append(ligne)
            continue

        # Inclure si universel ou si le rôle fait partie de la portée courante.
        if portee_courante is None or cible in portee_courante:
            result.append(ligne)

    return "".join(result)


def lire_contraintes(memory_dir: Path) -> str:
    """Lit `contraintes.md` si présent, sinon retombe sur `decisions.md`.

    Retourne une chaîne vide si les deux fichiers sont absents — comportement
    identique à l'ancienne lecture directe de `decisions.md`.
    """
    contraintes = memory_dir / "contraintes.md"
    if contraintes.exists():
        return contraintes.read_text(encoding="utf-8")
    decisions = memory_dir / "decisions.md"
    return decisions.read_text(encoding="utf-8") if decisions.exists() else ""


#: Le titre sous lequel `_build_project_context` place les ADR.
_SECTION = "## Décisions récentes"

#: Premier titre de niveau 2 qui n'est pas un en-tête ADR.
#: Marque la frontière entre les décisions et ce qui les suit (diff, tests, audit).
_SECTION_NON_ADR = re.compile(r"^## (?!ADR-\d+\b)", re.MULTILINE)


def _separer_decisions_et_queue(decisions: str) -> tuple[str, str]:
    """Sépare les blocs ADR de ce qui les suit dans le contexte.

    Returns (decisions_part, queue) where decisions_part contains only the
    ## ADR-NNN blocks and queue contains everything from the first non-ADR
    level-2 header onward (diff, test results, audit, etc.).
    """
    m = _SECTION_NON_ADR.search(decisions)
    if m is None:
        return decisions, ""
    return decisions[: m.start()], decisions[m.start() :]


def adr_pertinents(contexte_projet: str, role: str) -> str:
    """Réduit la section « Décisions récentes » d'un contexte projet à ce rôle.

    Détecte le format du contenu : si des blocs `## ADR-xxx` sont présents,
    c'est le format `decisions.md` et `adr_pour` s'applique. Sinon, c'est le
    format `contraintes.md` et `contraintes_pour` s'applique.

    Ce qui suit la section des décisions (diff, résultats du testeur, audit)
    est toujours rendu intact, quel que soit le rôle.

    Un contexte sans section de décisions traverse intact : c'est le cas d'un
    projet qui n'en a pas encore, et celui de la plupart des tests.
    """
    tete, separateur, decisions = contexte_projet.partition(_SECTION)
    if not separateur:
        return contexte_projet
    if _DEBUT_ADR.search(decisions):
        decisions_part, queue = _separer_decisions_et_queue(decisions)
        filtrees = adr_pour(decisions_part, role)
    else:
        decisions_part = decisions
        queue = ""
        filtrees = contraintes_pour(decisions_part, role)
    return tete + separateur + filtrees + queue
