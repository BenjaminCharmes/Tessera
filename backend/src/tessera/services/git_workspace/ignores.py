"""Pathspecs of Tessera's own artifacts and ignored-file purging."""

import asyncio

from tessera.services.git_workspace.chemins import _ORCHESTRATOR_ARTIFACT_PATHS, _RUN_POLICY_PATHS
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.socle import GitCore
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitIgnores(GitCore):
    """Pathspecs of Tessera's own artifacts and ignored-file purging."""

    async def _exclude_pathspecs(self) -> tuple[str, ...]:
        """Les `:(exclude)` à poser, sans ceux que le dépôt ignore déjà.

        Nommer un chemin **déjà ignoré** dans un pathspec fait sortir
        `git add` en code 1 (« The following paths are ignored… »), alors que
        la même commande sans ce pathspec réussit et saute le chemin en
        silence. Sur un projet en mode artefacts `local` (ADR-021), où
        `tickets/` et `memory/` sont dans `.git/info/exclude`, ces exclusions
        n'étaient donc pas seulement inutiles : elles faisaient échouer le
        commit de fin de run, et donc le run entier (ticket-072).

        Les fichiers de politique du run (`_RUN_POLICY_PATHS`) sont également
        exclus : un réglage effectué dans l'IDE pendant le run ne doit jamais
        se retrouver dans le commit du ticket (ticket-296, ADR-027).
        """
        # Boucle explicite : une compréhension contenant un `await` produit un
        # générateur asynchrone, pas un tuple.
        pathspecs: list[str] = []
        for chemin in (*_ORCHESTRATOR_ARTIFACT_PATHS, *_RUN_POLICY_PATHS):
            if not await self._is_ignored(chemin):
                pathspecs.append(f":(exclude){chemin}")
        return tuple(pathspecs)

    async def _is_ignored(self, path: str) -> bool:
        """True si le dépôt ignore ce chemin (`.gitignore` ou `.git/info/exclude`)."""
        proc = await asyncio.create_subprocess_exec(
            "git", "check-ignore", "-q", "--", path,
            cwd=str(self._project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def _purger_stage_ignoré(self) -> None:
        """Retire de l'index les fichiers désormais couverts par `.gitignore`.

        `git add -A` ne dé-stage pas les fichiers déjà dans l'index — même
        stagés comme intent-to-add — si une règle `.gitignore` les couvre
        après coup. Cette méthode ferme ce gap : les fichiers listés par
        `git ls-files --cached --ignored` ne doivent pas finir dans le commit.

        Les artefacts de tenue de livres (`_ORCHESTRATOR_ARTIFACT_PATHS`) sont
        gérés par `commit_bookkeeping` et sont donc exclus ici.

        Un fichier déjà présent dans `HEAD` reste dans l'index : le dépôt le
        suivait avant la règle d'exclusion, et son retrait se décide, il ne
        se fait pas en silence dans le commit d'un run (ticket-446).
        """
        try:
            out = await self._run(
                "ls-files", "--cached", "--ignored", "--exclude-standard"
            )
        except GitCommandError as exc:
            _logger.warning("staged_ignored_list_failed", extra={"error": str(exc)})
            return
        suivis = await self._chemins_dans_head()
        to_remove = [
            p for p in out.splitlines()
            if p and p not in suivis and not any(
                p.startswith(a.rstrip("/")) for a in _ORCHESTRATOR_ARTIFACT_PATHS
            )
        ]
        if not to_remove:
            return
        try:
            await self._run("rm", "--cached", "--", *to_remove)
        except GitCommandError as exc:
            _logger.warning(
                "staged_ignored_cleanup_failed",
                extra={"error": str(exc), "paths": to_remove},
            )

    async def _chemins_dans_head(self) -> frozenset[str]:
        """Chemins du commit `HEAD`, dans la même notation que `ls-files`.

        Vide sur un dépôt sans commit : la purge garde alors son comportement
        d'origine.
        """
        try:
            out = await self._run("ls-tree", "-r", "--name-only", "HEAD")
        except GitCommandError:
            return frozenset()
        return frozenset(p for p in out.splitlines() if p)
