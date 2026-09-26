"""A repository map in the coder's context — ticket-190.

Sur un run type, le codeur faisait 13 `Glob` et une cinquantaine de `Read`
avant sa première écriture, et relisait à chaque run les mêmes fichiers de
configuration. Chaque tour renvoie tout l'historique : cette découverte se
paie multipliée par le nombre de tours.
"""
import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.carte_du_depot import CarteDuDepot, replier
from tessera.services.politique_run import PolitiqueRun
from tests.test_orchestrator import (
    _make_agent_result,
    _make_orchestrator,
    _noop,
)


async def _git(cwd: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


async def _repo(root: Path, fichiers: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    for chemin, contenu in fichiers.items():
        fichier = root / chemin
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(contenu, encoding="utf-8")
    await _git(root, "add", "-A")
    await _git(root, "commit", "-q", "-m", "init")


# ------------------------------------------------------------------
# Le service
# ------------------------------------------------------------------


async def test_la_carte_ne_liste_que_les_fichiers_suivis(tmp_path: Path) -> None:
    # `git ls-files` respecte `.gitignore` : `node_modules` et les artefacts
    # de build n'ont rien à faire dans une carte qui doit tenir en 6 000
    # caractères.
    root = tmp_path / "projet"
    await _repo(root, {
        "README.md": "# p\n", ".gitignore": "dist/\n", "src/app.py": "x\n",
    })
    (root / "dist").mkdir()
    (root / "dist" / "bundle.js").write_text("ignoré", encoding="utf-8")
    (root / "brouillon.txt").write_text("non suivi", encoding="utf-8")

    carte = await CarteDuDepot(root).rendre()

    assert "src/app.py" in carte
    assert "README.md" in carte
    assert "dist/bundle.js" not in carte
    assert "brouillon.txt" not in carte


async def test_un_dossier_sans_depot_git_donne_une_carte_vide(tmp_path: Path) -> None:
    # `ensure_clean_tree` a déjà refusé avant, mais le service doit tenir seul :
    # une carte est une aide, jamais une raison de faire tomber un run.
    dossier = tmp_path / "pas-un-depot"
    dossier.mkdir()
    (dossier / "a.py").write_text("x", encoding="utf-8")

    assert await CarteDuDepot(dossier).rendre() == ""


async def test_en_git_root_ancestor_la_carte_part_de_la_racine_du_depot(
    tmp_path: Path,
) -> None:
    # Le projet bootstrap travaille dans `backend/` et `frontend/`, au-dessus
    # de son propre dossier : une carte limitée à `projects/ide-core` ne lui
    # dirait rien d'utile (ADR-028).
    depot = tmp_path / "depot"
    await _repo(depot, {
        "backend/main.py": "x\n", "projects/ide-core/CLAUDE.md": "# ide-core\n",
    })
    projet = depot / "projects" / "ide-core"

    ancetre = await CarteDuDepot.depuis(projet, PolitiqueRun(git_root="ancestor")).rendre()
    propre = await CarteDuDepot.depuis(projet, PolitiqueRun()).rendre()

    assert "backend/main.py" in ancetre
    assert "backend/main.py" not in propre
    assert "CLAUDE.md" in propre


# ------------------------------------------------------------------
# Le repliement
# ------------------------------------------------------------------


def test_replier_garde_une_liste_courte_telle_quelle() -> None:
    chemins = ["src/a.py", "src/b.py", "README.md"]
    assert replier(chemins).splitlines() == ["README.md", "src/a.py", "src/b.py"]


def test_replier_au_dela_de_400_entrees_replie_les_dossiers_les_plus_peuples() -> None:
    chemins = [f"src/module{m:02d}/fichier{f:02d}.py" for m in range(15) for f in range(30)]
    chemins += ["README.md", "pyproject.toml"]

    lignes = replier(chemins).splitlines()

    assert len(lignes) <= 400
    assert "README.md" in lignes
    assert any(ligne.startswith("src/module") and "(30 fichiers)" in ligne for ligne in lignes)


def test_replier_tient_sous_6000_caracteres() -> None:
    chemins = [
        f"un/chemin/vraiment/long/pour/le/test/dossier{d:02d}/fichier{f:03d}.py"
        for d in range(8) for f in range(45)
    ]
    rendu = replier(chemins)
    assert len(rendu) <= 6000
    assert "(45 fichiers)" in rendu


def test_replier_compte_les_sous_dossiers_deja_replies() -> None:
    # Replier `src/` après ses modules doit dire 60 fichiers, pas 0 : sinon la
    # carte ment sur ce qu'elle cache.
    chemins = [f"src/m{m}/f{f}.py" for m in range(2) for f in range(30)]
    rendu = replier(chemins, max_entrees=1)
    assert rendu.strip() == "src/ (60 fichiers)"


# ------------------------------------------------------------------
# Le pipeline
# ------------------------------------------------------------------


class _CarteFixe:
    async def rendre(self) -> str:
        return "src/unique.py\nREADME.md"


def _runner(calls: list[dict[str, Any]]) -> Any:
    reviews = 0

    async def fake_run(**kwargs: Any) -> AgentResult:
        nonlocal reviews
        calls.append(kwargs)
        if kwargs["role"] == AgentRole.reviewer:
            reviews += 1
            verdict = "CHANGES_REQUESTED: encore" if reviews == 1 else "APPROVED"
            return _make_agent_result(verdict, AgentRole.reviewer)
        result = _make_agent_result("code", AgentRole.codeur)
        result.session_id = "sess-1"
        return result

    runner = MagicMock()
    runner.run = fake_run
    return runner


async def test_le_codeur_recoit_la_carte_et_le_reviewer_non(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(tmp_path, runner=_runner(calls), carte_du_depot=_CarteFixe())
    await orc.run_pipeline("proj", "ticket-001", _noop)

    codeur = [c for c in calls if c["role"] == AgentRole.codeur][0]
    reviewer = [c for c in calls if c["role"] == AgentRole.reviewer][0]
    assert "## Fichiers du projet" in codeur["project_context"]
    assert "src/unique.py" in codeur["project_context"]
    assert "## Fichiers du projet" not in reviewer["project_context"]


async def test_la_carte_precede_les_decisions_pour_survivre_au_filtre_adr(
    tmp_path: Path,
) -> None:
    # `adr_pertinents` découpe tout ce qui suit « ## Décisions récentes » en
    # ADR : une carte placée après serait avalée par le dernier ADR, et
    # disparaîtrait avec lui si sa portée exclut le codeur.
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_runner(calls), carte_du_depot=_CarteFixe(),
        project_context="## Décisions récentes\n## ADR-001 — x\n**Portée** : architect\n",
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    contexte = [c for c in calls if c["role"] == AgentRole.codeur][0]["project_context"]
    assert contexte.index("## Fichiers du projet") < contexte.index("## Décisions récentes")


async def test_un_codeur_qui_reprend_sa_session_ne_recoit_pas_la_carte(
    tmp_path: Path,
) -> None:
    # Il l'a déjà (ticket-187) : la répéter paierait ce que la reprise évite.
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(tmp_path, runner=_runner(calls), carte_du_depot=_CarteFixe())
    await orc.run_pipeline("proj", "ticket-001", _noop)

    codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert len(codeur) == 2
    assert "## Fichiers du projet" not in codeur[1]["project_context"]


async def test_une_carte_qui_leve_ne_fait_pas_tomber_le_run(tmp_path: Path) -> None:
    class _CarteCassee:
        async def rendre(self) -> str:
            raise OSError("git absent")

    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(tmp_path, runner=_runner(calls), carte_du_depot=_CarteCassee())
    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is True
    assert "## Fichiers du projet" not in calls[0]["project_context"]
