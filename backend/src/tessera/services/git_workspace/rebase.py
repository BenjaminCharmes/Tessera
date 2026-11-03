"""Replaying a branch on its base, with abort and recovery."""

import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.services.git_workspace.chemins import (
    _JOURNAL_UNION_SUFFIXES,
    _is_orchestrator_artifact_path,
    _relatif_au_projet,
)
from tessera.services.git_workspace.conflits_regles import GitConflictsRegles
from tessera.services.git_workspace.erreurs import BaseIntrouvable, GitCommandError
from tessera.services.git_workspace.textes import _extraire_fichiers_bloques
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitRebase(GitConflictsRegles):
    """Replaying a branch on its base, with abort and recovery."""

    async def rejouer_sur(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]:
        """Rejoue la branche courante sur `base`. Rend les fichiers en conflit.

        Un rebase abouti renumérote ensuite les migrations Prisma du ticket
        qui prennent un numéro déjà pris par la base (ticket-484).
        """
        self.migrations_renumerotees = ()
        self.regles_appliquees = ()
        # Dans un worktree de run, la base locale est celle du checkout : on
        # rejoue sur le distant, que la livraison vient de rafraîchir.
        cible = f"origin/{base}" if self._worktree is not None else base
        conflits = await self._rebaser(cible, resolveur)
        if not conflits:
            await self._renumeroter_migrations(cible)
        return conflits

    async def _rebaser(
        self,
        base: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> tuple[str, ...]:
        """Rejoue la branche courante sur `base`. Rend les fichiers en conflit.

        Une branche partie d'une base qui a depuis avancé produit une PR que
        GitHub déclare non mergeable : attendre sa CI ne mènerait nulle part.

        Sans `resolveur`, un conflit **annule** le rebase et laisse la branche
        exactement comme elle était. Avec, le résolveur est appelé pendant le
        rebase et peut réécrire les fichiers ; s'il aboutit, le rebase se
        termine. Sinon — il lève, il laisse des marqueurs, il oublie un
        fichier — tout est annulé.

        **L'arbre ne reste jamais à mi-rebase.** Le ticket suivant démarrerait
        dessus, et l'utilisateur hériterait d'un dépôt qu'il n'a pas choisi.
        """
        await self._ensure_own_repository()
        self.raison_resolveur = None
        if not await self._ref_existe(base):
            raise BaseIntrouvable(base)

        sha_avant = (await self._run("rev-parse", "HEAD")).strip()

        try:
            await self._run("rebase", base)
        except GitCommandError as echec:
            refus = echec
        else:
            return ()

        conflits = await self._fichiers_en_conflit()
        if not conflits:
            # Un rebase refusé **sans conflit** n'a rien laissé en cours : la
            # commande s'est arrêtée avant de commencer — arbre sale, base
            # inconnue. `--abort` levait alors à son tour, et son « no rebase
            # in progress » remontait à la place de la vraie cause : la
            # livraison du premier run approuvé s'est plainte de l'annulation,
            # jamais de l'arbre que le pipeline venait de salir (ticket-159).
            await self._annuler_si_en_cours()
            raise refus

        # Résolution en union pour les fichiers journal (ticket-391, ADR-035) :
        # pipeline-log.md et documentation.json ne font qu'ajouter des entrées,
        # donc une union ne laisse jamais de contenu ambigu.
        # Les chemins de `git diff` partent de la racine du dépôt : sous
        # `git_root: ancestor`, seuls ceux du projet lui-même comptent.
        prefixe = (await self._run("rev-parse", "--show-prefix")).strip()
        relatifs = [_relatif_au_projet(c, prefixe) for c in conflits]
        if all(r is not None and r in _JOURNAL_UNION_SUFFIXES for r in relatifs):
            if await self._resoudre_conflits_journal_en_union(conflits):
                return ()

        # Si tous les conflits sont des artefacts Tessera, les résoudre
        # automatiquement en faveur de la branche (ticket-300, ADR-033).
        if all(r is not None and _is_orchestrator_artifact_path(r) for r in relatifs):
            if await self._resoudre_conflits_artefacts(conflits):
                return ()

        # Deux ajouts de bloc au même schéma Prisma : rien n'est édité des deux
        # côtés, inutile d'appeler un agent (ticket-484).
        if all(r is not None and r.endswith(".prisma") for r in relatifs):
            if await self._resoudre_prisma_en_ajouts(conflits, prefixe):
                return ()

        return await self._regles_puis_resolveur(conflits, prefixe, resolveur, sha_avant)

    async def _regles_puis_resolveur(
        self,
        conflits: tuple[str, ...],
        prefixe: str,
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]] | None,
        sha_avant: str,
    ) -> tuple[str, ...]:
        """Règles déterministes d'abord ; le résolveur ne reçoit que le reste (ticket-548).

        Les règles ne sont notées dans `regles_appliquees` que si le rebase
        aboutit : un rebase annulé n'a rien résolu.
        """
        restants, appliquees = await self._resoudre_par_regles(conflits, prefixe)
        if restants:
            if resolveur is None or not await self._faire_resoudre(restants, resolveur):
                await self._annuler_rebase_robuste(sha_avant)
                return restants
        else:
            try:
                await self._run("-c", "core.editor=true", "rebase", "--continue")
            except GitCommandError:
                # Le commit suivant peut entrer en conflit à son tour : la liste
                # de fichiers qu'on tient est périmée, on n'envoie rien au résolveur.
                await self._annuler_rebase_robuste(sha_avant)
                return conflits
        self.regles_appliquees = appliquees
        return ()

    async def _ref_existe(self, ref: str) -> bool:
        """La ref est-elle résolvable ici ?

        Vérifié **avant** de rejouer : sinon la cause remonte dans les mots de
        git, et la vraie information — un réglage à écrire — se perd.
        """
        try:
            await self._run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        except GitCommandError:
            return False
        return True

    async def _annuler_si_en_cours(self) -> None:
        """Annule le rebase s'il y en a un, sans jamais masquer l'erreur d'origine."""
        if await self._rebase_en_cours():
            try:
                await self._run("rebase", "--abort")
            except GitCommandError as exc:
                _logger.warning("rebase_abort_failed", extra={"error": str(exc)})

    async def _annuler_rebase_robuste(self, sha_avant: str) -> None:
        """Abort the rebase even when untracked Tessera files block ``--abort``.

        Sequence:
        1. Try ``rebase --abort``.
        2. On failure: remove any Tessera artifact paths that are blocking the
           reset (parsed from stderr), then retry ``--abort``.
        3. Last resort: manually remove the rebase state directory and
           hard-reset HEAD to *sha_avant*.

        Blocking paths come from git relative to the **repository root**, not
        the project directory.  For a project with ``git_root: ancestor`` the
        two differ (e.g. the git root is ``tessera/``, the project is
        ``tessera/projects/ide-core/``), so the absolute path is resolved from
        the git root and then re-expressed relative to the project before
        calling ``_is_orchestrator_artifact_path``.
        """
        try:
            await self._run("rebase", "--abort")
            return
        except GitCommandError as echec:
            bloquants = _extraire_fichiers_bloques(echec.stderr)
            artefacts_supprimes: list[str] = []
            if bloquants:
                git_root = await self._chemin_racine_git()
                project_root = self._project_path.resolve()
                for chemin_git in bloquants:
                    abs_path = (git_root / chemin_git).resolve()
                    try:
                        rel = str(abs_path.relative_to(project_root)).replace("\\", "/")
                    except ValueError:
                        continue
                    if _is_orchestrator_artifact_path(rel) and abs_path.is_file():
                        abs_path.unlink()
                        artefacts_supprimes.append(chemin_git)
                        _logger.info(
                            "artefact_supprime_pour_rebase_abort",
                            extra={"chemin": chemin_git},
                        )
            if artefacts_supprimes:
                try:
                    await self._run("rebase", "--abort")
                    return
                except GitCommandError:
                    pass

        _logger.warning("rebase_abort_dernier_recours", extra={"sha": sha_avant[:7]})
        await self._restaurer_depuis_sha(sha_avant)

    async def _chemin_racine_git(self) -> Path:
        """Return the absolute path of the git repository root (``--show-toplevel``)."""
        try:
            top = (await self._run("rev-parse", "--show-toplevel")).strip()
            return Path(top).resolve()
        except GitCommandError:
            return self._project_path.resolve()

    async def _restaurer_depuis_sha(self, sha: str) -> None:
        """Remove rebase state and hard-reset the branch to *sha*.

        Called only when both ``rebase --abort`` attempts have failed. Reads
        the original branch name from ``.git/rebase-merge/head-name`` before
        deleting the state directory so we can check it back out.
        """
        try:
            git_dir_str = (await self._run("rev-parse", "--git-dir")).strip()
            git_dir = Path(git_dir_str)
            if not git_dir.is_absolute():
                git_dir = self._project_path / git_dir
            head_name_file = git_dir / "rebase-merge" / "head-name"
            head_name = (
                head_name_file.read_text(encoding="utf-8").strip()
                if head_name_file.exists()
                else None
            )
            for nom in ("rebase-merge", "rebase-apply"):
                d = git_dir / nom
                if d.exists():
                    shutil.rmtree(str(d))
                    _logger.info("rebase_etat_supprime", extra={"dossier": nom})
            if head_name and head_name.startswith("refs/heads/"):
                branch = head_name[len("refs/heads/"):]
                try:
                    await self._run("checkout", branch)
                except GitCommandError:
                    pass
        except (GitCommandError, OSError) as exc:
            _logger.warning("rebase_etat_suppression_echoue", extra={"erreur": str(exc)})
        try:
            await self._run("reset", "--hard", sha)
        except GitCommandError as exc:
            _logger.error("rebase_reset_hard_echoue", extra={"erreur": str(exc)})
