"""Ce qu'on donne à lire aux agents ne se contredit pas — ticket-091.

Panne vécue : `projects/ide-core/CLAUDE.md` est `@`-importé dans **chaque**
session et enseignait `gh pr create --base main` + `gh pr merge --squash`,
c'est-à-dire l'exact inverse du flux du dépôt. Le skill `ticket-workflow`, lui,
était juste — mais il ne se charge qu'à la demande. La consigne fausse était
donc toujours en contexte, la bonne seulement parfois.

Il portait aussi `GH_CONFIG_DIR=/Users/<moi>/.config/gh`, un chemin d'une autre
machine, dans un dépôt utilisé sur deux postes.
"""
import re
import subprocess
from pathlib import Path

import pytest

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


#: Ce que chaque session paie avant d'avoir rien lu (ticket-246). Chaque ligne
#: concurrence les autres pour l'attention du modèle : au-delà, on retire, on
#: n'ajoute pas.
_BUDGETS_CLAUDE_MD = {"CLAUDE.md": 7_000, "projects/ide-core/CLAUDE.md": 6_000}


@pytest.mark.parametrize(("chemin", "budget"), sorted(_BUDGETS_CLAUDE_MD.items()))
def test_les_claude_md_tiennent_leur_budget(chemin: str, budget: int) -> None:
    taille = len(_lire(chemin))

    assert taille <= budget, f"{chemin} : {taille} caractères pour {budget} permis"


def test_les_skills_annonces_existent() -> None:
    # `CLAUDE.md` liste les skills disponibles. Un nom qui ne correspond à
    # rien envoie Claude chercher un fichier absent.
    annonces = set(
        re.findall(r"`([a-z][a-z-]+)`", _lire("CLAUDE.md").split("Skills disponibles")[-1].split("\n\n")[0])
    )
    presents = {d.name for d in (_RACINE / ".claude/skills").iterdir() if d.is_dir()}

    assert annonces <= presents, f"annoncés mais absents : {sorted(annonces - presents)}"


def test_aucune_command_ne_porte_le_nom_d_un_skill() -> None:
    # Claude Code sert le skill quand une command porte le même nom : la
    # command n'est alors jamais lue (ticket-261).
    dossier = _RACINE / ".claude/commands"
    commands = {f.stem for f in dossier.glob("*.md")} if dossier.is_dir() else set()
    skills = {d.name for d in (_RACINE / ".claude/skills").iterdir() if d.is_dir()}

    assert not commands & skills, f"command et skill homonymes : {sorted(commands & skills)}"


def test_l_arborescence_decrite_existe() -> None:
    # `CLAUDE.md` décrit `.claude/` : ce qu'il montre doit exister, sinon il
    # décrit un dépôt imaginaire.
    #
    # Sauf ce qu'il annonce lui-même comme gitignoré. Ce test exigeait la
    # présence de `settings.local.json`, que le dépôt s'interdit de versionner :
    # il passait sur le poste de son auteur et échouait sur tout clone neuf,
    # CI comprise (ticket-109). Le marqueur est déjà dans le texte, il suffit
    # de le lire.
    manquants = _json_decrits_manquants(_lire("CLAUDE.md"), _RACINE / ".claude")

    assert manquants == [], f"décrits dans .claude/ mais absents : {manquants}"


def _json_decrits_manquants(texte: str, racine: Path) -> list[str]:
    """Les `.json` que le texte décrit, qui n'existent pas et qu'il n'excuse pas."""
    decrit = set(re.findall(r"^\s{2,4}([a-z_.]+\.json|[a-z-]+/)", texte, re.MULTILINE))
    ignores = {
        nom
        for ligne in texte.splitlines()
        if "gitignor" in ligne.lower()
        for nom in re.findall(r"([a-z_.]+\.json)", ligne)
    }
    return sorted(
        d for d in decrit - ignores
        if d.endswith(".json") and not (racine / d).exists()
    )


def test_l_exemption_de_gitignore_ne_couvre_que_ce_qui_est_annonce(
    tmp_path: Path,
) -> None:
    """L'exemption se prouve sur un texte factice, pas sur `CLAUDE.md`.

    Aujourd'hui le seul `.json` que `CLAUDE.md` décrit est celui qu'il annonce
    gitignoré : le test ci-dessus ne verrouille donc plus rien tant que c'est
    le cas. Sans ce test-ci, l'exemption ajoutée par ticket-109 aurait vidé le
    verrou en silence.
    """
    texte = (
        "```\n"
        "  .claude/\n"
        "    settings.local.json   ← préférences personnelles (gitignoré)\n"
        "    registre.json         ← versionné, doit exister\n"
        "```\n"
    )

    # Les deux sont absents, mais un seul est excusé.
    assert _json_decrits_manquants(texte, tmp_path) == ["registre.json"]

    (tmp_path / "registre.json").write_text("{}", encoding="utf-8")
    assert _json_decrits_manquants(texte, tmp_path) == []


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

    from tessera.models.agent import AgentPipelineConfig
    from tessera.services import orchestrator as orch_service
    from tessera.routers import orchestrator as orch_router

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


def test_une_derogation_est_datee_et_porte_sa_condition_de_retrait() -> None:
    # Une exception écrite comme une règle devient une règle. Celle de
    # ticket-095 — merger sans CI parce que les minutes sont épuisées — doit
    # rester lisible comme temporaire, sinon dans trois semaines elle se lira
    # comme la façon de faire de ce dépôt.
    incompletes = []
    for consigne in _CONSIGNES:
        texte = _lire(consigne)
        for bloc in re.findall(
            r"Dérogation temporaire.*?(?=\n\n[^>]|\Z)", texte, re.DOTALL
        ):
            if not re.search(r"\d{4}-\d{2}-\d{2}", bloc):
                incompletes.append(f"{consigne} : sans date")
            if "À supprimer" not in bloc:
                incompletes.append(f"{consigne} : sans condition de retrait")

    assert incompletes == [], incompletes


# ------------------------------------------------------------------
# L'ancien nom ne revient pas — ticket-099
# ------------------------------------------------------------------

#: Le seul jeton qui survit au renommage : la clef que huit manifestes
#: portaient déjà sur disque, dont des dépôts clients. Elle reste lue pour ne
#: pas les faire basculer en silence sur le défaut fermé d'ADR-023 (ADR-036).
#: On la retire du texte avant de chercher, plutôt que d'exempter des fichiers
#: entiers — sinon la garde ne couvrirait plus rien de ce qu'ils contiennent.
_CLEF_HISTORIQUE = "vibe_artifacts"

#: Les fichiers qui enregistrent un état passé, et ce test qui nomme
#: forcément ce qu'il interdit.
_ANCIEN_NOM_TOLERE = {
    "docs/superpowers",
    "backend/tests/test_consignes_coherentes.py",
    "projects/ide-core/tickets",
}

def _fichiers_du_depot() -> list[str]:
    """Les fichiers suivis par git, et eux seuls.

    Balayer le disque attrapait `.env`, les caches de pytest et les artefacts
    detaches : des fichiers locaux, souvent porteurs de secrets, qu'aucun
    renommage de ce depot ne doit pretendre corriger.
    """
    sortie = subprocess.run(
        ["git", "ls-files"],
        cwd=_RACINE,
        capture_output=True,
        text=True,
        check=True,
    )
    return [c for c in sortie.stdout.splitlines() if c]


def test_l_ancien_nom_ne_reapparait_pas() -> None:
    # Un renommage qui n'est pas mesuré se défait ticket par ticket : il
    # suffit d'un import copié depuis un fichier ancien pour que les deux
    # noms coexistent, et plus personne ne sait lequel fait foi.
    fautifs = []
    for relatif in _fichiers_du_depot():
        fichier = _RACINE / relatif
        # `projects/` porte les projets de l'utilisateur : leurs manifestes
        # et leurs tickets ne sont pas à nous, sauf ceux d'ide-core.
        if relatif.startswith("projects/") and not relatif.startswith("projects/ide-core/"):
            continue
        if any(relatif.startswith(t) for t in _ANCIEN_NOM_TOLERE):
            continue
        try:
            texte = fichier.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"vibe", texte.replace(_CLEF_HISTORIQUE, ""), re.IGNORECASE):
            fautifs.append(relatif)

    assert not fautifs, (
        "L'ancien nom est revenu dans : "
        + ", ".join(sorted(fautifs))
        + ". Le produit s'appelle Tessera (ADR-036)."
    )


def test_aucune_clef_du_manifeste_genere_n_est_morte() -> None:
    """Chaque clef écrite dans un `agents.json` généré est lue quelque part.

    `max_instances` y était écrit à 2 pour le codeur et lu nulle part : le
    backend ne contient aucun `asyncio.gather`, le pipeline est strictement
    séquentiel. C'est le défaut que ticket-091 a nettoyé sur
    `auto_merge_on_approve` — un réglage qu'on lit et qu'on croit.

    Le test balaie les sources plutôt que d'énumérer une liste : une clef
    ajoutée au générateur sans lecteur tombe ici, sans qu'on ait pensé à elle.
    """
    import json

    from tessera.services.project_loader import _default_agents_json

    manifeste = json.loads(_default_agents_json("p", [], "tracked"))

    mortes = _clefs_mortes(manifeste)
    assert mortes == [], f"clefs écrites dans agents.json mais jamais lues : {mortes}"


def _clefs_mortes(manifeste: dict[str, object]) -> list[str]:
    """Les clefs d'un `agents.json` qu'aucun code ne consomme."""
    clefs = set(manifeste) - {"project_id"}
    pipeline = manifeste.get("pipeline")
    if isinstance(pipeline, dict):
        clefs |= set(pipeline)
    agents = manifeste.get("agents")
    if isinstance(agents, list):
        for agent in agents:
            clefs |= set(agent)

    sources = ""
    for chemin in (_RACINE / "backend" / "src").rglob("*.py"):
        sources += chemin.read_text(encoding="utf-8")

    # Une clef est « lue » si elle est **consommée** quelque part. Déclarer un
    # champ de modèle ne compte pas : `max_instances` était un champ d'
    # `AgentConfig`, ce qui suffisait à le faire passer pour lu alors que rien
    # ne s'en servait. Le générateur et les déclarations de modèles sont donc
    # retirés des sources avant la recherche.
    exclus = [
        _RACINE / "backend" / "src" / "tessera" / "services" / "project_loader.py",
        _RACINE / "backend" / "src" / "tessera" / "models" / "agent.py",
    ]
    ailleurs = sources
    for chemin in exclus:
        ailleurs = ailleurs.replace(chemin.read_text(encoding="utf-8"), "")

    return sorted(c for c in clefs if c not in ailleurs)


def test_le_manifeste_d_ide_core_ne_porte_aucune_clef_morte() -> None:
    """Le manifeste du projet bootstrap est tenu au même contrat que ceux générés.

    Le test précédent verrouille ce que `_default_agents_json` écrit, pas ce
    qui est déjà sur disque : `projects/ide-core/agents.json` portait encore
    `auto_merge_on_approve` — retiré du modèle au ticket-091 — et
    `max_instances`, jamais lu. Le projet qui construit l'IDE est celui qu'on
    ouvre en premier pour comprendre un `agents.json` ; un réglage mort y
    enseigne une fausse règle à qui le lit.
    """
    import json

    manifeste = json.loads(_lire("projects/ide-core/agents.json"))

    mortes = _clefs_mortes(manifeste)
    assert mortes == [], f"clefs mortes dans projects/ide-core/agents.json : {mortes}"


# ------------------------------------------------------------------
# La section « Agents actifs » suit le manifeste — ticket-249
# ------------------------------------------------------------------


def test_la_section_agents_actifs_suit_le_manifeste() -> None:
    """The « Agents actifs » section names exactly the manifest's active roles.

    Panne vécue : `agents.json` déclarait huit rôles actifs quand la section
    n'en nommait que trois — `doc-technique`, `doc-fonctionnelle` et
    `project-analyzer` n'apparaissaient nulle part dans le fichier importé à
    chaque session. Rien ne confrontait les deux : c'est l'angle mort qui a
    laissé la liste diverger (audit du 2026-09-29).
    """
    import json

    manifeste = json.loads(_lire("projects/ide-core/agents.json"))
    actifs = {a["role"] for a in manifeste["agents"] if a.get("active")}

    texte = _lire("projects/ide-core/CLAUDE.md")
    section = re.search(
        r"^## Agents actifs sur ce projet\n(.*?)(?=\n## |\n---)", texte, re.M | re.S
    )
    assert section, "section « Agents actifs sur ce projet » introuvable"
    nommes = set(re.findall(r"^- `([a-z-]+)`", section.group(1), re.M))

    assert nommes == actifs, (
        f"manquants dans CLAUDE.md : {sorted(actifs - nommes)} ; "
        f"nommés mais inactifs ou absents du manifeste : {sorted(nommes - actifs)}"
    )


# ------------------------------------------------------------------
# Le dossier et le champ disent la même chose — ticket-113
# ------------------------------------------------------------------


def test_le_dossier_d_un_ticket_correspond_a_son_champ_status() -> None:
    """Chaque ticket est rangé dans le dossier que son frontmatter annonce.

    La règle existe depuis le début — « changer de statut = déplacer le
    fichier **et** mettre à jour le champ, les deux, sinon l'UI et le fichier
    divergent » — et rien ne la mesurait. Elle reposait sur la discipline de
    celui qui range, et cette discipline a lâché trois fois sur douze tickets
    au cours d'une seule session : le travail fini, la PR ouverte, le
    déplacement oublié.

    ADR-034 : un budget que rien ne mesure est un souhait. Une règle non plus.
    """
    tickets = _RACINE / "projects" / "ide-core" / "tickets"
    divergents: list[str] = []

    for dossier in sorted(p for p in tickets.iterdir() if p.is_dir()):
        for fichier in sorted(dossier.glob("ticket-*.md")):
            entete = fichier.read_text(encoding="utf-8").split("---")[1]
            declare = next(
                (
                    l.split(":", 1)[1].strip()
                    for l in entete.splitlines()
                    if l.startswith("status:")
                ),
                None,
            )
            if declare != dossier.name:
                divergents.append(
                    f"{fichier.name} est dans {dossier.name}/ "
                    f"mais déclare status: {declare}"
                )

    assert divergents == [], "\n".join(divergents)


# ------------------------------------------------------------------
# Un numéro d'ADR cité doit exister quelque part — ticket-131
# ------------------------------------------------------------------


def _numeros_declares() -> set[str]:
    """Les ADR en vigueur, plus ceux qu'on a archivés."""
    numeros: set[str] = set()
    for nom in ("decisions.md", "decisions-archive.md"):
        chemin = _RACINE / "projects" / "ide-core" / "memory" / nom
        if chemin.exists():
            numeros |= set(
                re.findall(r"^## (ADR-\d{3})", chemin.read_text(encoding="utf-8"), re.M)
            )
    return numeros


def test_tout_adr_cite_existe_encore() -> None:
    # Le risque de l'archivage n'est pas d'archiver trop peu, c'est d'archiver
    # une contrainte encore appliquée : elle disparaîtrait du prompt sans que
    # rien n'échoue, et un agent la violerait des semaines plus tard sans
    # qu'on sache pourquoi.
    declares = _numeros_declares()
    assert declares, "aucun ADR trouvé — le chemin du fichier a bougé"

    cites: dict[str, set[str]] = {}
    for dossier, motifs in (
        ("backend/src", ("*.py",)),
        ("agents/prompts", ("*.md",)),
        (".claude/skills", ("*.md",)),
        ("frontend/src", ("*.ts", "*.tsx")),
    ):
        racine = _RACINE / dossier
        if not racine.is_dir():
            continue
        for motif in motifs:
            for fichier in racine.rglob(motif):
                texte = fichier.read_text(encoding="utf-8", errors="ignore")
                for numero in re.findall(r"ADR-\d{3}", texte):
                    cites.setdefault(numero, set()).add(
                        str(fichier.relative_to(_RACINE))
                    )

    inconnus = {n: sorted(f) for n, f in cites.items() if n not in declares}
    assert inconnus == {}, f"ADR cités mais introuvables : {inconnus}"


def test_l_archive_n_est_importee_nulle_part() -> None:
    # Elle existe pour *sortir* du prompt : l'importer annulerait le ticket.
    for claude_md in _RACINE.rglob("CLAUDE.md"):
        if ".venv" in claude_md.parts or "node_modules" in claude_md.parts:
            continue
        texte = claude_md.read_text(encoding="utf-8", errors="ignore")
        assert "decisions-archive" not in texte, (
            f"{claude_md} importe l'archive : elle repartirait dans chaque appel"
        )


# ------------------------------------------------------------------
# Traçabilité contraintes.md — ticket-311
# ------------------------------------------------------------------


def _audit_classement() -> dict[str, str]:
    """Retourne {ADR-xxx: classement} depuis adr-audit.md."""
    chemin = _RACINE / "projects/ide-core/memory/adr-audit.md"
    if not chemin.exists():
        return {}
    contenu = chemin.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for m in re.finditer(
        r"^\|\s*(\d+)\s*\|[^|]*\|\s*(règle|fusion|histoire|obsolète)\s*\|",
        contenu,
        re.MULTILINE,
    ):
        numero = f"ADR-{m.group(1).zfill(3)}"
        result[numero] = m.group(2).strip()
    return result


def test_tracabilite_chaque_regle_sans_portee_est_citee_dans_contraintes() -> None:
    """Tout ADR classé « règle » ou « fusion » sans **Portée** est cité dans contraintes.md.

    La portée d'un ADR le réserve à certains rôles. Sans portée, la règle
    vaut pour tous — et elle doit donc apparaître dans contraintes.md, le
    fichier qui remplace decisions.md dans le prompt des agents.
    Une règle absente de contraintes.md serait silencieusement ignorée.
    """
    from tessera.services.adr import decouper, portee_de

    decisions = _lire("projects/ide-core/memory/decisions.md")
    audit = _audit_classement()
    contraintes = _lire("projects/ide-core/memory/contraintes.md")

    assert audit, "adr-audit.md vide ou introuvable"
    assert contraintes, "contraintes.md vide ou introuvable"

    blocs = {b.numero: b for b in decouper(decisions)}
    # ADRs classés « règle » ou « fusion » sans portée dans decisions.md
    a_verifier = {
        numero
        for numero, classement in audit.items()
        if classement in ("règle", "fusion")
        and numero in blocs
        and portee_de(blocs[numero]) is None
    }
    manquants = sorted(n for n in a_verifier if n not in contraintes)

    assert manquants == [], (
        f"ADR règle/fusion sans portée absents de contraintes.md : {manquants}"
    )


def test_contraintes_md_tient_sous_12000_caracteres() -> None:
    taille = len(_lire("projects/ide-core/memory/contraintes.md"))

    assert taille <= 12_000, (
        f"contraintes.md : {taille} caractères pour 12 000 permis"
    )
