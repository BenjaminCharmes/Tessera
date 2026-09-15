# Pipeline sur diff réel — plan d'implémentation (phase 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire travailler le pipeline sur l'état réel du dépôt — une branche git par exécution, et un `git diff` en entrée du reviewer, de l'auditeur sécurité et du validateur — au lieu de la prose produite par le codeur.

**Architecture :** Un `GitWorkspaceService` encapsule les trois opérations git dont l'orchestrateur a besoin (créer la branche, lire le diff, committer). L'orchestrateur crée la branche avant le premier tour, lit le diff après chaque passage du codeur, et le transmet aux agents de contrôle à la place de `codeur_result.content`. Rien n'atteint `main` sans geste humain.

**Tech Stack :** Python 3.11, `asyncio.create_subprocess_exec` pour git, FastAPI, pytest, uv.

## Contexte hérité du ticket-044

Le codeur écrit désormais réellement dans le workspace via le Claude Agent SDK, avec `cwd` pointant sur le répertoire du projet. C'est ce qui rend cette phase possible : avant, il n'y avait aucun changement sur disque à différ.

Trois consommateurs reçoivent aujourd'hui `codeur_result.content` — la prose de l'agent — là où ils devraient voir le code :

| Consommateur | Signature actuelle | Ce qu'il reçoit aujourd'hui |
|---|---|---|
| `SecurityAuditorService.audit` | `audit(code_diff: str, project_path: Path)` | le texte du codeur |
| `ValidatorService.validate` | `validate(criteria, code_produced: str, test_result)` | le texte du codeur |
| Reviewer (via `AgentRunner`) | `project_context` enrichi | le texte du codeur dans le contexte |

Les deux premiers nomment déjà leur paramètre d'après ce qu'il devrait être. Aucune signature ne change dans ce plan — seul l'appelant change ce qu'il y met.

## État de départ

`uv run pytest -q` depuis `backend/` → **518 passés, 11 en échec, 2 désélectionnés.**

Les 11 échecs sont des défauts environnementaux Windows préexistants, suivis en issue #62 et **hors périmètre** : `UnicodeDecodeError` dans `test_github_sync.py` / `test_project_loader.py` (lectures sans `encoding="utf-8"` explicite), `OSError` dans `test_project_importer.py` (les symlinks exigent le mode développeur). Toute autre suite rouge est une vraie régression.

Les 2 désélectionnés sont les tests d'intégration facturés, exclus par `addopts = "-m 'not integration'"`.

## Global Constraints

- Type hints partout, sans exception. `snake_case`. Docstrings en anglais ; commentaires en français uniquement s'ils portent du contexte métier.
- `async/await` partout ; aucun appel bloquant dans un chemin async. **En particulier : git s'invoque via `asyncio.create_subprocess_exec`, jamais via `subprocess.run`.** `services/git_clone.py` montre le motif établi dans ce dépôt.
- Fichiers de moins de 200 lignes ; un test par fonction publique au minimum.
- Commits en Conventional Commits, en anglais. Branche courante : `ticket-045-pipeline-diff-et-quota`. Aucun commit sur `main`.
- Toutes les commandes s'exécutent depuis `backend/` avec `uv run`.
- **Ne jamais stager avec `git add -A` ni `git add .`** — toujours des chemins explicites.
- Aucun `git push`, aucune fusion, aucune opération destructive sur le dépôt de l'utilisateur : ce service opère sur les projets du workspace, pas sur vibe-ide.

## File Structure

| Fichier | Responsabilité |
|---|---|
| `src/vibe_ide/services/git_workspace.py` (créer) | `GitWorkspaceService` — branche, diff, commit |
| `src/vibe_ide/services/orchestrator.py` (modifier) | Crée la branche, lit le diff, le transmet aux agents de contrôle |
| `src/vibe_ide/routers/orchestrator.py` (modifier) | Construit le `GitWorkspaceService` |
| `tests/test_git_workspace.py` (créer) | Tests sur de vrais dépôts git temporaires |
| `tests/test_orchestrator.py` (modifier) | Le diff réel atteint auditeur et validateur |

---

### Task 1: `GitWorkspaceService`

Les trois opérations git dont l'orchestrateur a besoin, isolées et testables seules. Testées contre de **vrais dépôts git temporaires**, pas des mocks : la valeur de ce service est précisément qu'il pilote git correctement, ce qu'un mock ne vérifierait pas.

**Files:**
- Create: `backend/src/vibe_ide/services/git_workspace.py`
- Test: `backend/tests/test_git_workspace.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `GitWorkspaceService(project_path: Path)`
  - `async create_branch(ticket_id: str, slug: str) -> str` — crée et bascule sur `ticket-<id>-<slug>`, renvoie le nom retenu
  - `async current_diff() -> str` — `git diff` de l'arbre de travail, fichiers non suivis inclus
  - `async commit_all(message: str) -> str | None` — commite tout le travail, renvoie le SHA court, ou `None` s'il n'y avait rien à committer
  - `GitCommandError(Exception)` — porte `command`, `returncode`, `stderr`
  - `NotAGitRepository(GitCommandError)`

- [ ] **Step 1: Write the failing tests**

Créer `backend/tests/test_git_workspace.py` :

```python
import asyncio
from pathlib import Path

import pytest

from vibe_ide.services.git_workspace import (
    GitCommandError,
    GitWorkspaceService,
    NotAGitRepository,
)


async def _git(cwd: Path, *args: str) -> None:
    """Runs a git command in the test fixture, failing loudly."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """A real git repository with one commit on the default branch."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@vibe-ide.local")
    await _git(root, "config", "user.name", "vibe-ide test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def test_create_branch_bascule_dessus(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    name = await service.create_branch("ticket-001", "ajouter-la-feature-x")
    assert name == "ticket-001-ajouter-la-feature-x"

    proc = await asyncio.create_subprocess_exec(
        "git", "branch", "--show-current",
        cwd=str(repo), stdout=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    assert out.decode().strip() == name


async def test_create_branch_tronque_et_assainit_le_slug(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    name = await service.create_branch("ticket-002", "Ajouter  Des/Accents Éèà !! " + "x" * 80)
    assert name.startswith("ticket-002-")
    assert len(name) <= 60
    assert all(c.isalnum() or c == "-" for c in name)
    assert "--" not in name


async def test_create_branch_reutilise_une_branche_existante(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    first = await service.create_branch("ticket-003", "reprise")
    second = await service.create_branch("ticket-003", "reprise")
    assert first == second


async def test_current_diff_voit_un_fichier_modifie(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-004", "modif")
    (repo / "README.md").write_text("# projet modifie\n", encoding="utf-8")

    diff = await service.current_diff()
    assert "README.md" in diff
    assert "projet modifie" in diff


async def test_current_diff_voit_un_fichier_nouveau(repo: Path) -> None:
    # Un fichier non suivi n'apparaît pas dans un `git diff` nu : c'est
    # précisément le cas d'usage du codeur, qui crée des fichiers.
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-005", "ajout")
    (repo / "nouveau.py").write_text("def hello():\n    return 'bonjour'\n", encoding="utf-8")

    diff = await service.current_diff()
    assert "nouveau.py" in diff
    assert "bonjour" in diff


async def test_current_diff_vide_quand_rien_ne_change(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-006", "rien")
    diff = await service.current_diff()
    assert diff.strip() == ""


async def test_commit_all_renvoie_un_sha(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-007", "commit")
    (repo / "nouveau.py").write_text("x = 1\n", encoding="utf-8")

    sha = await service.commit_all("feat: ticket-007")
    assert sha is not None
    assert len(sha) >= 7
    assert (await service.current_diff()).strip() == ""


async def test_commit_all_renvoie_none_sans_changement(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-008", "vide")
    assert await service.commit_all("feat: rien") is None


async def test_repertoire_sans_depot_git_leve_not_a_git_repository(tmp_path: Path) -> None:
    service = GitWorkspaceService(tmp_path)
    with pytest.raises(NotAGitRepository):
        await service.create_branch("ticket-009", "sans-git")


async def test_git_command_error_porte_le_contexte(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    with pytest.raises(GitCommandError) as exc:
        await service.create_branch("ticket-010", "")
    assert exc.value.command
```

Note pour l'implémenteur : le dernier test suppose qu'un slug vide est refusé. Si tu juges qu'un slug vide doit au contraire produire `ticket-010` tout court, **dis-le et ajuste le test** — c'est un choix défendable, mais il doit être explicite et testé dans un sens ou dans l'autre.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_git_workspace.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vibe_ide.services.git_workspace'`.

- [ ] **Step 3: Write the implementation**

Créer `backend/src/vibe_ide/services/git_workspace.py`.

Points d'implémentation qui comptent :

- **Toujours `asyncio.create_subprocess_exec`**, jamais `subprocess.run` — le service est appelé depuis l'orchestrateur async. Suivre le motif de `services/git_clone.py`.
- **`current_diff()` doit inclure les fichiers non suivis.** Un `git diff` nu les ignore, or le codeur crée des fichiers : c'est le cas d'usage principal. La manière propre est `git add -A --intent-to-add` (ou `-N`) avant le `git diff`, ce qui rend les nouveaux fichiers visibles au diff sans les stager réellement.
- **Assainir le slug** : minuscules, accents et ponctuation ramenés à des tirets, tirets consécutifs fusionnés, tirets de bord retirés, longueur totale du nom bornée (60 caractères).
- **`create_branch` doit être idempotent** : si la branche existe déjà, basculer dessus plutôt qu'échouer. Un pipeline relancé sur le même ticket est un cas normal.
- **Décoder stdout/stderr en UTF-8 explicitement** (`.decode("utf-8", errors="replace")`). Sans cela, ce service reproduirait exactement le défaut d'encodage suivi en issue #62 sur les dépôts aux messages accentués.
- `GitCommandError` porte `command`, `returncode` et `stderr` pour que l'appelant puisse journaliser utilement.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_git_workspace.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: 518 passés + les nouveaux, 11 échecs connus, 2 désélectionnés.

- [ ] **Step 6: Commit**

```bash
git add backend/src/vibe_ide/services/git_workspace.py backend/tests/test_git_workspace.py
git commit -m "feat: add GitWorkspaceService for per-pipeline branches and diffs"
```

---

### Task 2: L'orchestrateur crée la branche et émet un event

**Files:**
- Modify: `backend/src/vibe_ide/services/orchestrator.py` — `EventType`, `Orchestrator.__init__`, `run_pipeline`
- Modify: `backend/src/vibe_ide/routers/orchestrator.py` — `_build_orchestrator`
- Test: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `GitWorkspaceService` (Task 1).
- Produces:
  - `EventType.BRANCH_CREATED = "branch_created"`
  - `Orchestrator(..., git_workspace: GitWorkspaceService | None = None)`
  - `PipelineResult` gagne `branch: str | None = None`

- [ ] **Step 1: Write the failing test**

Ajouter à `backend/tests/test_orchestrator.py` :

```python
async def test_run_pipeline_cree_une_branche_et_emet_l_event(tmp_path: Path) -> None:
    """La branche est créée avant le premier tour, et annoncée."""
    events: list[OrchestratorEvent] = []

    class FakeGit:
        def __init__(self) -> None:
            self.created: list[tuple[str, str]] = []

        async def create_branch(self, ticket_id: str, slug: str) -> str:
            self.created.append((ticket_id, slug))
            return f"{ticket_id}-{slug}"

        async def current_diff(self) -> str:
            return ""

        async def commit_all(self, message: str) -> str | None:
            return None

    git = FakeGit()
    orchestrator = _make_orchestrator(tmp_path, git_workspace=git)  # helper du fichier

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert len(git.created) == 1
    branch_events = [e for e in events if e.type == EventType.BRANCH_CREATED]
    assert len(branch_events) == 1
    assert branch_events[0].data["branch"] == git.created[0][0] + "-" + git.created[0][1]
    assert result.branch == branch_events[0].data["branch"]


async def test_run_pipeline_sans_git_workspace_reste_fonctionnel(tmp_path: Path) -> None:
    """git_workspace est optionnel : sans lui, le pipeline tourne comme avant."""
    events: list[OrchestratorEvent] = []
    orchestrator = _make_orchestrator(tmp_path, git_workspace=None)

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert not [e for e in events if e.type == EventType.BRANCH_CREATED]
    assert result.branch is None
```

Le helper `_make_orchestrator` existe déjà (`tests/test_orchestrator.py:45`) mais n'accepte aujourd'hui que `runner`, `ticket_service`, `project_context`, `agent_configs` et `max_review_rounds`. **Étends-le** avec `git_workspace`, `security_auditor`, `validator` et `project_path`, tous optionnels et par défaut `None`, pour que les tâches suivantes s'appuient dessus. N'altère aucun comportement asservi par les tests existants : ajouter des paramètres par défaut ne change rien pour les appelants actuels.

Les helpers `_make_ticket`, `_make_agent_result(content, role)` et `_noop` existent également — réutilise-les.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py -k branche -v`
Expected: FAIL — `TypeError` sur le paramètre `git_workspace` inconnu.

- [ ] **Step 3: Write the implementation**

Dans `services/orchestrator.py` :

Ajouter à l'enum `EventType`, après `AGENT_TOOL_USE` :

```python
    BRANCH_CREATED = "branch_created"
```

Ajouter le champ à `PipelineResult` :

```python
    branch: str | None = None
```

Ajouter le paramètre au constructeur (dernier, avec défaut `None`, pour ne casser aucun appelant) et le stocker.

Au début de `run_pipeline`, après avoir récupéré le ticket et **avant** la boucle de tours :

```python
        branch: str | None = None
        if self._git_workspace is not None:
            try:
                branch = await self._git_workspace.create_branch(ticket_id, ticket.title)
                await on_event(
                    OrchestratorEvent(
                        type=EventType.BRANCH_CREATED,
                        ticket_id=ticket_id,
                        data={"branch": branch},
                    )
                )
                self._log(f"[{ticket_id}] branche {branch}")
            except Exception as exc:
                # Un projet sans dépôt git reste utilisable : on continue sans
                # garde-fou de branche plutôt que d'interrompre le pipeline.
                _logger.warning("branch_creation_failed", extra={"error": str(exc)})
```

Renseigner `branch=branch` dans **chaque** construction de `PipelineResult` de la méthode — il y en a plusieurs (sortie sécurité, sortie approuvée, sortie épuisement des tours). Les repérer avec `grep -n "PipelineResult(" services/orchestrator.py`.

Dans `routers/orchestrator.py`, `_build_orchestrator` construit déjà `project_path` : ajouter

```python
    git_workspace = GitWorkspaceService(project_path)
```

et le passer à `Orchestrator(...)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: PASS, y compris tous les tests d'orchestrateur préexistants.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/orchestrator.py backend/src/vibe_ide/routers/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: create a dedicated git branch per pipeline run"
```

---

### Task 3: Le diff réel alimente l'auditeur, le validateur et le reviewer

Le cœur de la phase. Aucune signature ne change : seul l'appelant change ce qu'il transmet.

**Files:**
- Modify: `backend/src/vibe_ide/services/orchestrator.py` — `run_pipeline`
- Test: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `GitWorkspaceService.current_diff()` (Task 1), le champ `_git_workspace` (Task 2).
- Produces: rien de nouveau.

- [ ] **Step 1: Write the failing tests**

Ajouter à `backend/tests/test_orchestrator.py` :

```python
DIFF_REEL = "diff --git a/src/foo.py b/src/foo.py
+SECRET = 'hunter2'
"


class _FakeGit:
    """GitWorkspaceService double returning a controlled diff."""

    def __init__(self, diff: str = DIFF_REEL) -> None:
        self._diff = diff
        self.commits: list[str] = []

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        return f"{ticket_id}-slug"

    async def current_diff(self) -> str:
        return self._diff

    async def commit_all(self, message: str) -> str | None:
        self.commits.append(message)
        return "abc1234"


class _RecordingRunner:
    """Minimal runner: returns fixed prose and records every call."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def run(self, **kwargs: object) -> AgentResult:
        self.calls.append(kwargs)
        role = kwargs["role"]
        content = (
            "APPROVED" if role == AgentRole.reviewer else "prose du codeur"
        )
        return _make_agent_result(content, role=role)  # type: ignore[arg-type]


async def test_l_auditeur_securite_recoit_le_diff_reel(tmp_path: Path) -> None:
    audits: list[str] = []

    class _FakeAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            audits.append(code_diff)
            return SecurityAuditResult(
                verdict="PASS", issues=[], has_critical=False,
                has_high=False, summary="rien",
            )

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(),
        security_auditor=_FakeAuditor(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert audits, "l'auditeur n'a pas été appelé"
    assert "SECRET = 'hunter2'" in audits[0]
    assert "prose du codeur" not in audits[0]


async def test_le_validateur_recoit_le_diff_reel(tmp_path: Path) -> None:
    validated: list[str] = []

    class _FakeValidator:
        async def validate(
            self, criteria: list[str], code_produced: str, test_result: object
        ) -> object:
            validated.append(code_produced)
            return ValidationResult(all_passed=True, criteria=[], verdict="APPROVED")

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(),
        validator=_FakeValidator(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert validated, "le validateur n'a pas été appelé"
    assert "SECRET = 'hunter2'" in validated[0]


async def test_le_reviewer_recoit_le_diff_reel(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=_FakeGit(), project_path=tmp_path
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert reviewer_calls, "le reviewer n'a pas été appelé"
    assert "SECRET = 'hunter2'" in str(reviewer_calls[0]["project_context"])


async def test_sans_git_workspace_on_retombe_sur_la_prose_du_codeur(
    tmp_path: Path,
) -> None:
    """Historical behaviour preserved when no git repository is available."""
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=None, project_path=tmp_path
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert "prose du codeur" in str(reviewer_calls[0]["project_context"])


async def test_diff_vide_retombe_sur_la_prose_du_codeur(tmp_path: Path) -> None:
    """An empty diff means the coder wrote nothing: its prose is the only
    material left."""
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=_FakeGit(diff="   
"),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert "prose du codeur" in str(reviewer_calls[0]["project_context"])
```

`_FakeGit` et `_RecordingRunner` servent aussi à la Task 4 — place-les au niveau module, pas dans une fonction. Importe `SecurityAuditResult` et `ValidationResult` depuis leurs services respectifs ; si leurs champs diffèrent de ce qui est écrit ici, **lis les dataclasses et ajuste** plutôt que de deviner.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py -k diff_reel -v`
Expected: FAIL — les consommateurs reçoivent encore `codeur_result.content`.

- [ ] **Step 3: Write the implementation**

Dans `run_pipeline`, juste après le retour du codeur et avant le bloc testeur, calculer une fois le contenu à transmettre :

```python
            # Le codeur écrit réellement sur disque : ce qui doit être relu,
            # audité et validé, c'est le diff, pas la prose de l'agent.
            reviewed_code = codeur_result.content
            if self._git_workspace is not None:
                try:
                    diff = await self._git_workspace.current_diff()
                    if diff.strip():
                        reviewed_code = diff
                except Exception as exc:
                    _logger.warning("diff_failed", extra={"error": str(exc)})
```

Puis remplacer les trois usages :

- `self._security_auditor.audit(code_diff=..., ...)` reçoit `reviewed_code`
- `self._validator.validate(..., code_produced=...)` reçoit `reviewed_code`
- le bloc de contexte du reviewer utilise `reviewed_code` à la place de `codeur_result.content`

Repérer les emplacements exacts avec `grep -n "codeur_result.content" services/orchestrator.py`.

Noter le repli en deux temps : pas de `git_workspace` **ou** diff vide ⇒ on garde le comportement historique. Un diff vide signifie que le codeur n'a rien écrit ; sa prose reste alors la seule matière disponible.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: aucune régression.

- [ ] **Step 6: Commit**

```bash
git add backend/src/vibe_ide/services/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: feed the real git diff to reviewer, security audit and validator"
```

---

### Task 4: Commit sur verdict APPROVED

**Files:**
- Modify: `backend/src/vibe_ide/services/orchestrator.py` — `run_pipeline`
- Test: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `GitWorkspaceService.commit_all()` (Task 1).
- Produces: `PipelineResult` gagne `commit_sha: str | None = None` ; `EventType.COMMIT_CREATED = "commit_created"`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_commit_sur_verdict_approuve(tmp_path: Path) -> None:
    """An approved pipeline commits on its branch."""
    events: list[OrchestratorEvent] = []
    git = _FakeGit()

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RecordingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert len(git.commits) == 1
    assert "ticket-001" in git.commits[0]
    assert result.commit_sha == "abc1234"

    commit_events = [e for e in events if e.type == EventType.COMMIT_CREATED]
    assert len(commit_events) == 1
    assert commit_events[0].data["sha"] == "abc1234"


async def test_pas_de_commit_sur_changes_requested(tmp_path: Path) -> None:
    """A non-approved pipeline leaves the work tree untouched for inspection."""
    git = _FakeGit()

    class _RefusingRunner(_RecordingRunner):
        async def run(self, **kwargs: object) -> AgentResult:
            self.calls.append(kwargs)
            role = kwargs["role"]
            content = (
                "CHANGES_REQUESTED: revoir la gestion d'erreur"
                if role == AgentRole.reviewer
                else "prose du codeur"
            )
            return _make_agent_result(content, role=role)  # type: ignore[arg-type]

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RefusingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert git.commits == []
    assert result.commit_sha is None


async def test_pas_de_commit_quand_la_securite_bloque(tmp_path: Path) -> None:
    """The early exit on BLOCK must not commit anything."""
    git = _FakeGit()

    class _BlockingAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            return SecurityAuditResult(
                verdict="BLOCK",
                issues=["secret en dur"],
                has_critical=True,
                has_high=True,
                summary="secret detecte",
            )

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=git,
        security_auditor=_BlockingAuditor(),
        project_path=tmp_path,
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert git.commits == []
    assert result.commit_sha is None
```

Ces tests réutilisent `_FakeGit` et `_RecordingRunner` introduits en Task 3.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py -k commit -v`
Expected: FAIL — `commit_sha` n'existe pas sur `PipelineResult`.

- [ ] **Step 3: Write the implementation**

Ajouter `COMMIT_CREATED = "commit_created"` à `EventType` et `commit_sha: str | None = None` à `PipelineResult`.

Dans la branche approuvée de `run_pipeline`, avant de construire le `PipelineResult` :

```python
                commit_sha: str | None = None
                if self._git_workspace is not None:
                    try:
                        commit_sha = await self._git_workspace.commit_all(
                            f"feat: {ticket_id} — {ticket.title}"
                        )
                        if commit_sha is not None:
                            await on_event(
                                OrchestratorEvent(
                                    type=EventType.COMMIT_CREATED,
                                    ticket_id=ticket_id,
                                    data={"sha": commit_sha, "branch": branch},
                                )
                            )
                    except Exception as exc:
                        _logger.warning("commit_failed", extra={"error": str(exc)})
```

Ne committer **que** sur le chemin approuvé. Les sorties par blocage sécurité et par épuisement des tours laissent l'arbre de travail intact — c'est ce qui permet à l'utilisateur d'inspecter ce qui a été produit.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/services/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: commit the work tree on an approved pipeline"
```

---

### Task 5: Supprimer la duplication de `project_context`

`project_context` est une chaîne pré-assemblée injectée dans le prompt de chaque agent. Le provider SDK charge déjà le `CLAUDE.md` du projet via son `cwd` : le conserver fait payer le même contenu deux fois, à chaque appel, pour chaque agent du pipeline.

**Files:**
- Modify: `backend/src/vibe_ide/routers/orchestrator.py` — construction de `project_context`
- Test: `backend/tests/test_orchestrator_router.py`

**Interfaces:**
- Consumes: `Settings.llm_provider`.
- Produces: rien de nouveau.

- [ ] **Step 1: Mesurer avant de couper**

Run: `grep -rn "project_context" backend/src/vibe_ide/`

Établir d'où vient le contenu injecté aujourd'hui et ce qu'il contient exactement. **Si `project_context` porte autre chose que le `CLAUDE.md` du projet** — des métadonnées de projet, une liste de tickets, un état — alors cette partie ne fait pas double emploi et doit être conservée. Rapporte ce que tu trouves avant de supprimer quoi que ce soit.

- [ ] **Step 2: Write the failing test**

```python
def test_project_context_ne_duplique_pas_claude_md_sur_le_provider_sdk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the SDK provider, CLAUDE.md is read via cwd — do not re-inject it."""
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text(
        "MARQUEUR_CLAUDE_MD_UNIQUE
", encoding="utf-8"
    )

    context = _build_project_context("mon-projet")  # nom réel à confirmer

    assert "MARQUEUR_CLAUDE_MD_UNIQUE" not in context


def test_project_context_conserve_claude_md_sur_le_provider_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On the Messages API there is no cwd: the injection is still needed."""
    monkeypatch.setattr(settings, "llm_provider", "anthropic_api")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text(
        "MARQUEUR_CLAUDE_MD_UNIQUE
", encoding="utf-8"
    )

    context = _build_project_context("mon-projet")

    assert "MARQUEUR_CLAUDE_MD_UNIQUE" in context
```

`_build_project_context` est un nom d'attente : l'assemblage se fait aujourd'hui dans `_build_orchestrator`. **Le Step 1 te dit où il vit réellement** — si la logique n'est pas extractible telle quelle, extrais-la en fonction testable dans le même module, ce qui est de toute façon la bonne forme pour la tester.

- [ ] **Step 3: Write the implementation**

Conditionner l'injection du `CLAUDE.md` dans `project_context` à `settings.llm_provider != "agent_sdk"`. Tout le reste du contexte — ce qui n'est pas le `CLAUDE.md` — est conservé dans les deux cas.

Commenter en français la raison : le SDK lit le fichier depuis `cwd`, la réinjection serait une double facturation.

- [ ] **Step 4: Run tests and the full suite**

Run: `uv run pytest -q`
Expected: aucune régression.

- [ ] **Step 5: Commit**

```bash
git add backend/src/vibe_ide/routers/orchestrator.py backend/tests/test_orchestrator_router.py
git commit -m "perf: stop duplicating CLAUDE.md into the prompt on the SDK provider"
```

---

## Après ce plan

Le pipeline travaille alors sur l'état réel du dépôt. La phase 5 fera l'objet d'un plan distinct : `QuotaTracker` alimenté par les `RateLimitEvent` du SDK, table `quota_events`, endpoint `/api/v1/usage`, mise en pause du mode autonome sur `status == "rejected"`, budget cumulatif par run (issue #61), et rendu des events `AGENT_TOOL_USE` et `BRANCH_CREATED` côté frontend.
