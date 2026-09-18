"""N'injecter à chaque agent que les ADR qui le contraignent — ticket-087.

`decisions.md` part **en entier** dans chaque appel d'agent, jusqu'à dix-huit
fois par ticket. À trente et un ADR il pèse plus de cinq mille tokens, et il
grossit à chaque décision.

Le coût n'est pas le vrai problème — c'est la dilution. Un codeur reçoit la
palette de couleurs, le choix de Tauri contre Electron et le gestionnaire de
paquets Python, au milieu des quelques contraintes qu'il doit réellement
respecter. Les règles qui comptent se noient dans celles qui ne le concernent
pas.

Un ADR déclare donc sa portée, en une ligne : `**Portée** : codeur, reviewer`.
**Sans portée, il vaut pour tous** — le défaut protège, comme partout ailleurs
ici. Rater une contrainte serait silencieux, et une contrainte qu'un agent
n'a pas lue n'en est plus une.
"""
import re
from dataclasses import dataclass

#: `## ADR-0xx — Titre` ouvre un bloc ; le suivant le ferme.
_DEBUT_ADR = re.compile(r"^##\s+(ADR-\d+)\b", re.MULTILINE)

#: `**Portée** : a, b` — la ligne, où qu'elle soit dans le bloc.
_PORTEE = re.compile(r"^\*\*Port[ée]e\*\*\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


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


#: Le titre sous lequel `_build_project_context` place les ADR.
_SECTION = "## Décisions récentes"


def adr_pertinents(contexte_projet: str, role: str) -> str:
    """Réduit la section « Décisions récentes » d'un contexte projet à ce rôle.

    Le contexte est assemblé une fois par run et sert à tous les agents ; le
    filtrage doit donc avoir lieu ici, au moment de rédiger le prompt, seul
    endroit où le rôle est connu.

    Un contexte sans section de décisions traverse intact : c'est le cas d'un
    projet qui n'en a pas encore, et celui de la plupart des tests.
    """
    tete, separateur, decisions = contexte_projet.partition(_SECTION)
    if not separateur:
        return contexte_projet
    return tete + separateur + adr_pour(decisions, role)
