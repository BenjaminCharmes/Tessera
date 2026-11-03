"""Relancer les tests quand le rebase ramène des commits de la base — ticket-568.

Le testeur a jugé la branche **avant** la livraison, sur une base qui a pu
avancer depuis. Le rebase de la phase 1 rejoue le travail sur la base d'aujourd'hui,
et un travail vert sur l'ancienne base peut casser sur la nouvelle : c'est ce
qui a laissé la PR #616 ouverte sur une CI rouge, alors que le testeur local
l'aurait vu en six minutes.

Ce module décide *si* il faut retester (la base a avancé) et *comment*
(la commande du testeur du run). Il ne pousse rien et ne décide pas de
l'arrêt : `LivraisonService` lit son résultat et s'arrête, ou non.
"""
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tessera.services.chaines_de_test import chaine_commune
from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd
from tessera.services.test_runner import TestCommandNotFound, TestResult, TestRunnerService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Longueur de la sortie des tests dans la ligne de journal, qui reste sur une ligne.
_LIGNE_MAX = 300
#: Longueur de la sortie des tests dans l'arrêt, que le ticket garde en entier.
_ARRET_MAX = 2000


@dataclass(frozen=True)
class ResultatRetest:
    """The outcome of the tests run after a rebase."""

    vert: bool
    resume: str
    details: str = ""


@dataclass(frozen=True)
class Jugement:
    """What the delivery records of a retest: its journal step, and the stop if red."""

    etape: str
    duree_ms: float
    #: `None` quand les tests sont verts : la livraison continue vers le push.
    arret: str | None


class _GitAncetre(Protocol):
    async def est_ancetre(self, ancetre: str, descendant: str) -> bool | None: ...

    async def chemins_modifies(self, gauche: str, droite: str) -> list[str] | None: ...


Lanceur = Callable[[], Awaitable[TestResult]]


def _resultat_de(resultat: TestResult) -> ResultatRetest:
    """Convert a test result; a run that did not finish is not a green one."""
    vert = resultat.passed and resultat.demarree and not resultat.expiree
    details = resultat.failure_details or "\n".join(resultat.errors)
    return ResultatRetest(
        vert=vert, resume=resultat.output_summary.strip(), details="" if vert else details
    )


class RetestApresRebase:
    """Decides whether the base moved, and reruns the project's tests when it did."""

    def __init__(
        self, git: _GitAncetre, lancer: Lanceur, worktree: bool, verifier: bool = False
    ) -> None:
        self._git = git
        self._lancer = lancer
        # Dans un worktree de run, la base locale est celle du checkout : le
        # rebase rejoue sur le distant, et c'est lui qu'on compare
        # (même règle que `GitWorkspaceService.rejouer_sur`).
        self._worktree = worktree
        # Le `test_cwd` du projet porte `scripts/verifier.py` : on sait alors
        # quelles chaînes un chemin touche, et la base n'oblige à retester que
        # si elle touche une chaîne de la branche (ticket-584).
        self._verifier = verifier

    async def base_a_avance(self, base: str) -> bool:
        """True when rebasing onto `base` brings something that can break the branch.

        À appeler **avant** le rebase. Échoue fermé (ADR-039) : si git ne sait
        pas dire, on suppose que la base a avancé, et les tests repassent.
        Avec `scripts/verifier.py`, une base qui n'a touché aucune chaîne que la
        branche touche aussi n'oblige pas à retester ; la CI rejoue tout.
        """
        cible = f"origin/{base}" if self._worktree else base
        try:
            dessous = await self._git.est_ancetre(cible, "HEAD")
        except Exception as exc:  # noqa: BLE001 — l'inconnu compte comme une avancée
            _logger.warning("base_avancee_illisible", extra={"erreur": str(exc)})
            return True
        if dessous is True:
            return False
        return await self._chaine_partagee(cible) if self._verifier else True

    async def _chaine_partagee(self, cible: str) -> bool:
        """True when base and branch touch a common chain; True too when unreadable."""
        try:
            de_la_base = await self._git.chemins_modifies("HEAD", cible)
            de_la_branche = await self._git.chemins_modifies(cible, "HEAD")
        except Exception as exc:  # noqa: BLE001 — l'inconnu compte comme une chaîne partagée
            _logger.warning("chemins_illisibles", extra={"erreur": str(exc)})
            return True
        if de_la_base is None or de_la_branche is None:
            return True
        return chaine_commune(de_la_base, de_la_branche)

    async def juger(self, base: str) -> "Jugement | None":
        """Rerun the tests and say what the delivery must record and whether it stops.

        `None` quand le projet n'a pas de test à lancer : aucune trace. Un premier
        essai rouge (échec, délai dépassé, démarrage raté) est relancé une fois : un
        test instable n'arrête pas, à lui seul, la livraison — mais l'instabilité
        reste écrite dans le journal.
        """
        t0 = time.monotonic()
        premier = await self.relancer()
        if premier is None:
            return None
        resultat = premier if premier.vert else await self.relancer()
        if resultat is None:
            return None
        etape = etape_de(resultat)
        if resultat.vert and premier is not resultat:
            etape = etape_au_second_essai(resultat, premier)
        return Jugement(
            etape=etape,
            duree_ms=(time.monotonic() - t0) * 1000,
            arret=None if resultat.vert else arret_de(resultat, base),
        )

    async def relancer(self) -> ResultatRetest | None:
        """Run the project's tests; None when the project has none to run.

        Un lanceur qui lève, une commande qui ne démarre pas ou un délai dépassé
        rendent un résultat rouge : rien ne prouve que le travail passe.
        """
        try:
            return _resultat_de(await self._lancer())
        except TestCommandNotFound:
            return None
        except Exception as exc:  # noqa: BLE001 — échoue fermé : pas de preuve, pas de push
            _logger.warning("retest_echoue", extra={"erreur": str(exc)})
            return ResultatRetest(
                vert=False, resume=f"les tests n'ont pas pu tourner : {type(exc).__name__}"
            )


def retest_du_run(
    git: _GitAncetre | None,
    worktree: bool,
    test_runner: TestRunnerService | None,
    project_path: Path,
    commande: str | None,
    test_cwd: str | None = None,
) -> RetestApresRebase | None:
    """The hook of a run, or None when it has no tester or no git space.

    Même testeur, même commande, même environnement que ceux du pipeline : le
    `TestRunnerService` du run porte déjà le `cwd`, le délai et l'environnement
    du worktree. Sans testeur, le projet n'a pas de tests à relancer.
    """
    if git is None or test_runner is None:
        return None

    async def lancer() -> TestResult:
        return await test_runner.run_tests(project_path, test_command=commande)

    return RetestApresRebase(git, lancer, worktree, _porte_un_verifier(project_path, test_cwd))


def _porte_un_verifier(project_path: Path, test_cwd: str | None) -> bool:
    """True when the project's `test_cwd` holds `scripts/verifier.py`."""
    try:
        dossier = resoudre_le_cwd(project_path.resolve(), test_cwd) if test_cwd else project_path
        return (dossier / "scripts" / "verifier.py").is_file()
    except (CommandeInvalide, OSError):
        # Sans verifier lisible, on retombe sur « la base a avancé → retest ».
        return False


def etape_de(resultat: ResultatRetest) -> str:
    """The one-line journal entry: the outcome, and the start of the output."""
    issue = "verts" if resultat.vert else "rouges"
    sortie = re.sub(r"\s+", " ", resultat.details or resultat.resume).strip()
    suite = f" ({sortie[:_LIGNE_MAX]})" if sortie else ""
    return f"tests relancés après rebase : {issue}{suite}"


def etape_au_second_essai(vert: ResultatRetest, premier: ResultatRetest) -> str:
    """The journal entry of a retest green on the second try, with the first failure."""
    sortie_verte = re.sub(r"\s+", " ", vert.resume).strip()
    echec = re.sub(r"\s+", " ", premier.details or premier.resume).strip()
    verte = f" ({sortie_verte[:_LIGNE_MAX]})" if sortie_verte else ""
    return (
        f"tests relancés après rebase : vert au 2e essai{verte} ; "
        f"1er essai rouge : {echec[:_LIGNE_MAX]}"
    )


def arret_de(resultat: ResultatRetest, base: str) -> str:
    """The stop line of a red retest: nothing is pushed, and the output says why."""
    sortie = (resultat.details or resultat.resume).strip()[:_ARRET_MAX]
    return (
        f"Tests rouges après rebase sur {base} : rien n'est poussé. "
        "La base a avancé pendant le run et le travail ne passe plus dessus."
        + (f"\n{sortie}" if sortie else "")
    )
