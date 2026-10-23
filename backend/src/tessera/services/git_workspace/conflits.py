"""Conflict resolution rules applied during a rebase."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.services.git_workspace.chemins import (
    _is_orchestrator_artifact_path,
    _relatif_au_projet,
)
from tessera.services.git_workspace.erreurs import GitCommandError
from tessera.services.git_workspace.socle import GitCore
from tessera.services.git_workspace.textes import _MARQUEUR_CONFLIT, _union_json_lists, _union_lines
from tessera.services.prisma_conflits import fusionner_ajouts, planifier_renumerotation
from tessera.utils.logger import get_logger


_logger = get_logger("tessera.services.git_workspace")


class GitConflicts(GitCore):
    """Conflict resolution rules applied during a rebase."""

    async def _resoudre_conflits_artefacts(self, conflits: tuple[str, ...]) -> bool:
        """Auto-resolve conflicts where all files are Tessera artifacts.

        Accepts the branch version (theirs) for each conflict:
        - UD (updated by base, deleted by branch): stage the deletion via
          ``git rm -f``.
        - Any other conflict: check out theirs and stage.

        Also stages any untracked Tessera artifact files (e.g. a ``done/``
        ticket the cherry-pick added alongside the conflict), so that
        ``rebase --continue`` can create a clean commit.

        Returns True when the rebase completed successfully, False on any error.
        """
        try:
            for chemin in conflits:
                # `:/<chemin>` : les chemins viennent de `git diff --name-only`,
                # relatifs à la racine du dépôt. Pour un projet déclaré
                # `git_root: ancestor`, le cwd est un sous-dossier du dépôt ;
                # un chemin nu serait résolu depuis ce cwd et ne désignerait
                # aucun fichier. `:/<chemin>` force la résolution depuis la
                # racine du dépôt, ce qui est correct pour les deux modes.
                pathspec = f":/{chemin}"
                status_out = await self._run("status", "--porcelain", "--", pathspec)
                code = status_out[:2] if len(status_out) >= 2 else "UU"  # noqa: PLR2004
                if code == "UD":
                    # Branch deleted the file; stage the deletion.
                    await self._run("rm", "-f", "--", pathspec)
                else:
                    await self._run("checkout", "--theirs", "--", pathspec)
                    await self._run("add", "--", pathspec)

            if await self._fichiers_en_conflit():
                return False

            # Stage any untracked Tessera artifacts the cherry-pick was adding
            # (e.g. a tickets/done/ file written alongside the conflict).
            listing = await self._run("ls-files", "--others", "--exclude-standard")
            for untracked in listing.splitlines():
                untracked = untracked.strip()
                if untracked and _is_orchestrator_artifact_path(untracked):
                    await self._run("add", "--", untracked)

            await self._run("-c", "core.editor=true", "rebase", "--continue")
            return True
        except GitCommandError:
            return False

    async def _resoudre_conflits_journal_en_union(
        self, conflits: tuple[str, ...]
    ) -> bool:
        """Résout en union les conflits sur les fichiers journal (ticket-391).

        Appelée uniquement quand tous les fichiers en conflit sont dans
        ``_JOURNAL_UNION_SUFFIXES``. Pour chaque fichier :
        - ``pipeline-log.md`` : union des lignes, base en premier ;
        - ``documentation.json`` : union des listes JSON sans doublon ;
          JSON illisible → renvoie False, le conflit reste non résolu.

        Renvoie True quand le rebase s'est poursuivi avec succès.
        """
        try:
            for chemin in conflits:
                # Stage 2 = ours (base sur laquelle on rejoue), stage 3 = theirs (ticket).
                try:
                    base_content = await self._run("show", f":2:{chemin}")
                except GitCommandError:
                    base_content = ""
                try:
                    theirs_content = await self._run("show", f":3:{chemin}")
                except GitCommandError:
                    theirs_content = ""

                if chemin.endswith("pipeline-log.md"):
                    resolved: str = _union_lines(base_content, theirs_content)
                elif chemin.endswith("documentation.json"):
                    maybe = _union_json_lists(base_content, theirs_content)
                    if maybe is None:
                        _logger.warning(
                            "journal_union_json_illisible", extra={"chemin": chemin}
                        )
                        return False
                    resolved = maybe
                else:
                    return False

                # git show :2:path retourne le chemin depuis la racine du dépôt.
                # Pour un projet déclaré git_root: ancestor, ce chemin inclut
                # le préfixe (ex. projects/ide-core/memory/…). On le retire pour
                # écrire dans le bon emplacement sur le disque.
                rel_in_project = chemin
                if self._travaille_dans_le_parent():
                    try:
                        prefix = (await self._run("rev-parse", "--show-prefix")).strip()
                        if prefix and rel_in_project.startswith(prefix):
                            rel_in_project = rel_in_project[len(prefix):]
                    except GitCommandError:
                        pass
                dest = self._project_path / rel_in_project
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(resolved, encoding="utf-8")
                # `:/` : `chemin` est relatif à la racine du dépôt, et le cwd
                # est le dossier du projet (git_root: ancestor).
                await self._run("add", "--", f":/{chemin}")

            _logger.info("journal_union_resolu", extra={"fichiers": list(conflits)})
            await self._run("-c", "core.editor=true", "rebase", "--continue")
            return True
        except GitCommandError:
            return False

    async def _etage_de_conflit(self, etage: int, chemin: str) -> str:
        """Contenu d'un étage du conflit (1 ancêtre, 2 base, 3 ticket) ; vide si absent."""
        try:
            return await self._run("show", f":{etage}:{chemin}")
        except GitCommandError:
            return ""

    async def _resoudre_prisma_en_ajouts(
        self, conflits: tuple[str, ...], prefixe: str
    ) -> bool:
        """Garde les blocs ajoutés des deux côtés d'un conflit `.prisma`.

        Tout est calculé avant la première écriture : si un seul fichier
        n'est pas un pur ajout, rien n'est touché et le résolveur reçoit les
        fichiers intacts. Rend True quand le rebase s'est poursuivi.
        """
        fusions: dict[str, str] = {}
        for chemin in conflits:
            fusion = fusionner_ajouts(
                await self._etage_de_conflit(2, chemin),
                await self._etage_de_conflit(3, chemin),
                await self._etage_de_conflit(1, chemin),
            )
            if fusion is None:
                return False
            fusions[chemin] = fusion
        try:
            for chemin, texte in fusions.items():
                dest = self._project_path / (_relatif_au_projet(chemin, prefixe) or chemin)
                dest.write_text(texte, encoding="utf-8", newline="")
                await self._run("add", "--", f":/{chemin}")
            _logger.info("prisma_ajouts_fusionnes", extra={"fichiers": list(conflits)})
            await self._run("-c", "core.editor=true", "rebase", "--continue")
        except GitCommandError:
            return False
        return True

    async def _dossiers_de_migrations(self, ref: str) -> set[str]:
        """Tous les dossiers de `ref` sous le projet, chemins relatifs au projet."""
        sortie = await self._run("ls-tree", "-r", "-d", "--name-only", ref)
        return set(sortie.splitlines())

    async def _renumeroter_migrations(self, base: str) -> None:
        """Renomme et commite les migrations du ticket qui collisionnent (ticket-484).

        Sans collision, aucune commande git d'écriture ne part. Un échec
        annule les renommages et laisse la branche comme le rebase l'a rendue.
        """
        plan = planifier_renumerotation(
            await self._dossiers_de_migrations(base),
            await self._dossiers_de_migrations("HEAD"),
        )
        if not plan:
            return
        try:
            for ancien, nouveau in plan:
                await self._run("mv", ancien, nouveau)
            titre = "; ".join(f"{a.rpartition('/')[2]} to {n.rpartition('/')[2]}" for a, n in plan)
            await self._run("commit", "-q", "-m", f"chore: renumber migration {titre}")
        except GitCommandError as exc:
            _logger.warning("migration_renumerotation_echec", extra={"erreur": str(exc)})
            await self._run("reset", "-q", "--hard", "HEAD")
            return
        for ancien, nouveau in plan:
            _logger.info("migration_renumerotee", extra={"ancien": ancien, "nouveau": nouveau})
        self.migrations_renumerotees = tuple(plan)

    async def _rebase_en_cours(self) -> bool:
        """Git a-t-il un rebase à moitié appliqué sous la main ?"""
        try:
            git_dir = Path((await self._run("rev-parse", "--git-dir")).strip())
        except GitCommandError:
            return False
        if not git_dir.is_absolute():
            git_dir = self._project_path / git_dir
        return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()

    async def _faire_resoudre(
        self,
        conflits: tuple[str, ...],
        resolveur: Callable[[tuple[str, ...]], Awaitable[None]],
    ) -> bool:
        """Laisse le résolveur réécrire les fichiers, puis poursuit le rebase.

        Rend `False` dès que quoi que ce soit ne va pas, et pose la cause dans
        `raison_resolveur`. L'appelant annule : aucun état intermédiaire n'a
        besoin d'être compris ici.
        """
        self.raison_resolveur = None
        try:
            await resolveur(conflits)
        except Exception as exc:  # noqa: BLE001 — un résolveur qui échoue fait annuler
            _logger.warning("resolveur_en_echec", extra={"fichiers": conflits})
            self.raison_resolveur = f"le résolveur a levé {type(exc).__name__}"
            return False

        self.raison_resolveur = self._raison_fichiers_resolus(conflits)
        if self.raison_resolveur is not None:
            return False

        try:
            await self._run("add", "--", *conflits)
            if await self._fichiers_en_conflit():
                self.raison_resolveur = "des conflits subsistent après la résolution"
                return False
            await self._run(
                "-c", "core.editor=true", "rebase", "--continue"
            )
        except GitCommandError as exc:
            self.raison_resolveur = (
                "git a refusé de poursuivre le rebase : "
                + (exc.stderr.strip() or str(exc))
            )
            return False
        return True

    def _raison_fichiers_resolus(self, conflits: tuple[str, ...]) -> str | None:
        """Pourquoi les fichiers laissés par le résolveur ne sont pas livrables."""
        for chemin in conflits:
            fichier = self._project_path / chemin
            if not fichier.is_file():
                return f"fichier introuvable après résolution : {chemin}"
            # Un fichier qui garde ses marqueurs compile rarement et se relit
            # encore moins : le committer serait pire que ne rien faire.
            if _MARQUEUR_CONFLIT in fichier.read_text(encoding="utf-8", errors="replace"):
                _logger.warning("marqueurs_restants", extra={"fichier": chemin})
                return f"marqueurs de conflit restants dans {chemin}"
        return None

    async def _fichiers_en_conflit(self) -> tuple[str, ...]:
        sortie = await self._run("diff", "--name-only", "--diff-filter=U")
        return tuple(ligne.strip() for ligne in sortie.splitlines() if ligne.strip())
