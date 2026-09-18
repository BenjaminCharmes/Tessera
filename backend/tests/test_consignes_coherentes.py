"""Ce qu'on donne à lire aux agents ne se contredit pas — ticket-091.

Panne vécue : `projects/ide-core/CLAUDE.md` est `@`-importé dans **chaque**
session et enseignait `gh pr create --base main` + `gh pr merge --squash`,
c'est-à-dire l'exact inverse du flux du dépôt. Le skill `ticket-workflow`, lui,
était juste — mais il ne se charge qu'à la demande. La consigne fausse était
donc toujours en contexte, la bonne seulement parfois.

Il portait aussi `GH_CONFIG_DIR=/Users/moi/.config/gh`, un chemin d'une autre
machine, dans un dépôt utilisé sur deux postes.
"""
import re
from pathlib import Path

_RACINE = Path(__file__).resolve().parents[2]

#: Tout ce qu'un agent — Claude Code ou agent du produit — reçoit comme
#: consigne. Les ADR n'en font pas partie : ils décrivent, ils n'instruisent
#: pas, et `decisions.md` a son propre budget.
_CONSIGNES = (
    "CLAUDE.md",
    "projects/ide-core/CLAUDE.md",
    *(str(p.relative_to(_RACINE)) for p in sorted((_RACINE / ".claude").rglob("*.md"))),
    *(str(p.relative_to(_RACINE)) for p in sorted((_RACINE / "agents/prompts").glob("*.md"))),
)


def _lire(chemin: str) -> str:
    fichier = _RACINE / chemin
    return fichier.read_text(encoding="utf-8") if fichier.is_file() else ""


def test_aucune_consigne_n_ouvre_une_pr_de_ticket_sur_main() -> None:
    # Le flux du dépôt est `ticket → develop → main`. Une PR de ticket ouverte
    # sur `main` court-circuite l'intégration, et `main` est la branche
    # publiable.
    fautifs = [
        c
        for c in _CONSIGNES
        if re.search(r"--base main(?!.*--head develop)", _lire(c))
    ]

    assert fautifs == [], f"PR de ticket dirigée vers main : {fautifs}"


def _blocs_de_code(texte: str) -> list[list[str]]:
    """Les blocs délimités par ``` — les commandes, pas la prose autour."""
    blocs: list[list[str]] = []
    courant: list[str] | None = None
    for ligne in texte.splitlines():
        if ligne.strip().startswith("```"):
            if courant is None:
                courant = []
            else:
                blocs.append(courant)
                courant = None
            continue
        if courant is not None:
            courant.append(ligne)
    return blocs


def test_aucun_bloc_ne_squashe_develop_dans_main() -> None:
    # Un squash de `develop` vers `main` réécrit les SHA : les deux branches
    # divergent définitivement, chaque merge suivant reproduit des conflits sur
    # du code déjà fusionné, et `main` perd l'historique par ticket.
    #
    # On lit les **blocs de code**, pas la prose : une phrase qui dit « pas de
    # squash » ou qui raconte l'erreur passée n'est pas une commande. Un test
    # qui se déclenche sur du texte correct finit par être ignoré.
    fautifs = []
    for consigne in _CONSIGNES:
        for bloc in _blocs_de_code(_lire(consigne)):
            vers_main = any("--base main" in l for l in bloc)
            squash = [
                l for l in bloc if "pr merge" in l and "--squash" in l and "PAS" not in l
            ]
            if vers_main and squash:
                fautifs.append(f"{consigne}: {squash[0].strip()[:60]}")

    assert fautifs == [], f"squash de develop vers main : {fautifs}"


def test_aucune_consigne_ne_code_en_dur_un_chemin_de_machine() -> None:
    # Le dépôt sert sur deux postes. Un chemin absolu d'une machine est faux
    # sur l'autre, et le reste en silence.
    motif = re.compile(r"(/Users/[A-Za-z]|C:\\Users\\|/home/[a-z])")
    fautifs = [c for c in _CONSIGNES if motif.search(_lire(c))]

    assert fautifs == [], f"chemin d'une machine précise : {fautifs}"


def test_les_skills_annonces_existent() -> None:
    # `CLAUDE.md` liste les skills disponibles. Un nom qui ne correspond à
    # rien envoie Claude chercher un fichier absent.
    annonces = set(
        re.findall(r"`([a-z][a-z-]+)`", _lire("CLAUDE.md").split("Skills disponibles")[-1].split("\n\n")[0])
    )
    presents = {d.name for d in (_RACINE / ".claude/skills").iterdir() if d.is_dir()}

    assert annonces <= presents, f"annoncés mais absents : {sorted(annonces - presents)}"


def test_l_arborescence_decrite_existe() -> None:
    # `CLAUDE.md` décrit `.claude/` : ce qu'il montre doit exister, sinon il
    # décrit un dépôt imaginaire.
    decrit = re.findall(r"^\s{2,4}([a-z_.]+\.json|[a-z-]+/)", _lire("CLAUDE.md"), re.MULTILINE)
    manquants = [
        d for d in set(decrit)
        if d.endswith(".json") and not (_RACINE / ".claude" / d).exists()
    ]

    assert manquants == [], f"décrits dans .claude/ mais absents : {manquants}"


# ------------------------------------------------------------------
# Une configuration qui ne configure rien — ticket-091
# ------------------------------------------------------------------


def test_aucun_reglage_de_pipeline_n_est_mort() -> None:
    # `auto_merge_on_approve` n'était lu nulle part, et `_default_agents_json`
    # l'écrivait à `true` dans chaque projet créé. Dans un produit dont toute
    # la question est de savoir qui a le droit de merger, un réglage nommé
    # « merge automatique » qui ne fait rien est pire qu'absent : on le lit et
    # on le croit.
    import inspect

    from vibe_ide.models.agent import AgentPipelineConfig
    from vibe_ide.services import orchestrator as orch_service
    from vibe_ide.routers import orchestrator as orch_router

    sources = inspect.getsource(orch_service) + inspect.getsource(orch_router)
    morts = [
        champ
        for champ in AgentPipelineConfig.model_fields
        if champ not in sources
    ]

    assert morts == [], f"réglages déclarés mais jamais lus : {morts}"


# ------------------------------------------------------------------
# Le budget des ADR — ticket-091
# ------------------------------------------------------------------

#: Le budget du skill `write-adr`. Un ADR sans portée part dans chaque appel
#: d'agent, jusqu'à dix-huit par ticket : sa longueur est une taxe permanente.
_BUDGET_MOTS = 160


def _adr() -> list[tuple[str, int]]:
    contenu = _lire("projects/ide-core/memory/decisions.md")
    blocs = re.split(r"\n(?=## ADR-)", contenu)
    return [
        (b.splitlines()[0][:60], len(b.split()))
        for b in blocs
        if b.startswith("## ADR-")
    ]


def test_aucun_adr_ne_depasse_le_budget() -> None:
    # Douze ADR sur trente et un le dépassaient, dont trois écrits le jour même
    # où le budget a été rappelé. Un budget que rien ne mesure n'est pas un
    # budget, c'est un souhait.
    hors = [f"{titre} : {mots} mots" for titre, mots in _adr() if mots > _BUDGET_MOTS]

    assert hors == [], f"au-dessus de {_BUDGET_MOTS} mots : {hors}"


def test_chaque_adr_porte_une_date_et_une_decision() -> None:
    contenu = _lire("projects/ide-core/memory/decisions.md")
    incomplets = [
        b.splitlines()[0][:60]
        for b in re.split(r"\n(?=## ADR-)", contenu)
        if b.startswith("## ADR-")
        and not ("**Date**" in b and "**Décision**" in b)
    ]

    assert incomplets == [], f"format incomplet : {incomplets}"
