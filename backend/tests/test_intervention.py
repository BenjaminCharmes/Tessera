"""Une intervention du superviseur : un run, un commit par action — ticket-854, ADR-080."""
import asyncio
from datetime import datetime
from pathlib import Path

from tessera.services.livraison.livraison_intervention import ControleDuDiff
from tessera.services.livraison.livraison_resultat import Livraison
from tessera.services.pipeline.run_registry import RunRegistry
from tessera.services.supervision.intervention import Application, Resultat, intervenir
from tessera.services.supervision.superviseur_actions import Action

_MAINTENANT = datetime(2026, 11, 6, 10, 15, 0)
_BRANCHE = "supervision-20261106-101500"


class _FauxChantier:
    """A chantier on a temp folder: files written there are 'modified' until committed."""

    def __init__(self, racine: Path, *, echec_commit: bool = False) -> None:
        self.racine = racine
        self.echec_commit = echec_commit
        self.ouvert = False
        self.ferme = False
        self.commits: list[tuple[str, list[str]]] = []
        self.livraisons: list[tuple[str, str]] = []
        self.controle: ControleDuDiff | None = None
        self.en_attente: set[str] = set()
        self.pr_number: int | None = 5

    async def ouvrir(self, branche: str) -> Path:
        self.ouvert = True
        return self.racine

    async def fichiers_modifies(self) -> list[str]:
        courants = {p.relative_to(self.racine).as_posix() for p in self.racine.rglob("*") if p.is_file()}
        return sorted(courants - {c for _, chemins in self.commits for c in chemins} | self.en_attente)

    async def commiter(self, message: str, chemins: list[str]) -> str | None:
        if self.echec_commit:
            raise RuntimeError("git commit a échoué")
        self.commits.append((message, list(chemins)))
        return f"{len(self.commits):x}" * 40

    async def livrer(self, branche: str, sha: str, controle: ControleDuDiff, titre: str) -> Livraison:
        self.livraisons.append((branche, sha))
        self.controle = controle
        return Livraison(pr_number=self.pr_number)

    async def fermer(self) -> None:
        self.ferme = True


def _ecrire_un_ticket(chemin: str = "tickets/todo/ticket-900-x.md") -> object:
    async def appliquer(projet: Path) -> Application:
        fichier = projet / chemin
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text("# t\n", encoding="utf-8")
        return Application(cible="ticket-900", resume="tri du ticket")

    return appliquer


async def _intervenir(
    tmp_path: Path, chantier: _FauxChantier, appliquer: object, registre: RunRegistry | None = None,
    delai_max_s: float = 1.0,
) -> Resultat:
    return await intervenir(
        "demo", Action.TRIER, appliquer,  # type: ignore[arg-type]
        registre=registre or RunRegistry(), nouveau_chantier=lambda _pid: chantier,
        delai_max_s=delai_max_s, maintenant=lambda: _MAINTENANT,
    )


async def test_intervention_waits_for_the_running_run_then_writes(tmp_path: Path) -> None:
    registre = RunRegistry()
    run = registre.ouvrir("demo", "ticket-001", mode="single")
    chantier = _FauxChantier(tmp_path)

    tache = asyncio.create_task(
        _intervenir(tmp_path, chantier, _ecrire_un_ticket(), registre, delai_max_s=5.0)
    )
    await asyncio.sleep(0.05)
    assert not chantier.ouvert and not tache.done()

    registre.fermer(run.run_id)
    resultat = await asyncio.wait_for(tache, 2.0)

    assert resultat.statut == "livre" and chantier.ouvert and chantier.ferme
    assert not registre.projet_occupe("demo")


async def test_intervention_does_not_write_while_a_queue_holds_the_project(tmp_path: Path) -> None:
    registre = RunRegistry()
    file = registre.ouvrir("demo", None, mode="queue")
    chantier = _FauxChantier(tmp_path)

    tache = asyncio.create_task(
        _intervenir(tmp_path, chantier, _ecrire_un_ticket(), registre, delai_max_s=5.0)
    )
    await asyncio.sleep(0.05)
    assert not chantier.ouvert and chantier.commits == []

    registre.fermer(file.run_id)
    resultat = await asyncio.wait_for(tache, 2.0)
    assert resultat.statut == "livre"


async def test_intervention_gives_up_after_the_delay_without_writing(tmp_path: Path) -> None:
    registre = RunRegistry()
    registre.ouvrir("demo", None, mode="autonomous")
    chantier = _FauxChantier(tmp_path)

    resultat = await _intervenir(tmp_path, chantier, _ecrire_un_ticket(), registre, delai_max_s=0.05)

    assert resultat.statut == "abandonne"
    assert not chantier.ouvert and chantier.commits == [] and chantier.livraisons == []
    assert list(tmp_path.rglob("*.md")) == []
    assert registre.projet_tenu_par_file("demo")


async def test_forbidden_path_in_diff_cancels_everything(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    async def appliquer(projet: Path) -> Application:
        for chemin in ("tickets/todo/ticket-900-x.md", "backend/src/x.py"):
            (projet / chemin).parent.mkdir(parents=True, exist_ok=True)
            (projet / chemin).write_text("x\n", encoding="utf-8")
        return Application(cible="ticket-900", resume="tri")

    resultat = await _intervenir(tmp_path, chantier, appliquer)

    assert resultat.statut == "blocked" and resultat.raison is not None and "x.py" in resultat.raison
    assert chantier.livraisons == []
    assert all("blocked" in message for message, _ in chantier.commits)
    assert not (tmp_path / "memory" / "supervision.md").exists()
    assert chantier.ferme


async def test_action_cannot_write_the_journal_itself(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    async def appliquer(projet: Path) -> Application:
        (projet / "memory").mkdir()
        (projet / "memory" / "supervision.md").write_text("faux\n", encoding="utf-8")
        return Application(cible="x", resume="y")

    resultat = await _intervenir(tmp_path, chantier, appliquer)

    assert resultat.statut == "blocked" and chantier.livraisons == []


async def test_one_action_makes_one_commit_and_one_journal_line(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    resultat = await _intervenir(tmp_path, chantier, _ecrire_un_ticket())

    action, journal = chantier.commits
    assert action[0] == "chore(supervision): trier ticket-900"
    assert action[1] == ["tickets/todo/ticket-900-x.md"]
    assert journal[1] == ["memory/supervision.md"]
    lignes = [
        ligne for ligne in (tmp_path / "memory" / "supervision.md").read_text(encoding="utf-8").splitlines()
        if ligne.startswith("- ")
    ]
    assert len(lignes) == 1
    sha = resultat.sha
    assert sha is not None and f"| {sha[:7]} |" in lignes[0]
    assert resultat.branche == _BRANCHE and resultat.pr_number == 5
    assert chantier.livraisons == [(_BRANCHE, "2" * 40)]
    assert chantier.controle is not None and chantier.controle(["tickets/todo/a.md"]) is None
    assert chantier.controle(["backend/a.py"]) is not None


async def test_nothing_changed_commits_and_delivers_nothing(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    async def appliquer(projet: Path) -> Application:
        return Application(cible="ticket-900", resume="rien à trier")

    resultat = await _intervenir(tmp_path, chantier, appliquer)

    assert resultat.statut == "rien" and chantier.commits == [] and chantier.livraisons == []
    assert chantier.ferme


async def test_delivery_stop_leaves_the_work_local(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)
    chantier.pr_number = None

    resultat = await _intervenir(tmp_path, chantier, _ecrire_un_ticket())

    assert resultat.statut == "local" and resultat.pr_number is None


async def test_exception_ends_blocked_with_a_commit(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path)

    async def appliquer(projet: Path) -> Application:
        (projet / "tickets").mkdir()
        (projet / "tickets" / "a.md").write_text("a\n", encoding="utf-8")
        raise RuntimeError("l'action a échoué en route")

    registre = RunRegistry()
    resultat = await _intervenir(tmp_path, chantier, appliquer, registre)

    assert resultat.statut == "blocked" and resultat.raison is not None
    assert "l'action a échoué" in resultat.raison
    assert len(chantier.commits) == 1
    assert chantier.commits[0][0].startswith("chore(supervision): trier blocked")
    assert chantier.commits[0][1] == ["tickets/a.md"]
    assert chantier.livraisons == [] and chantier.ferme
    assert not registre.projet_occupe("demo")


async def test_failed_commit_ends_blocked_without_raising(tmp_path: Path) -> None:
    chantier = _FauxChantier(tmp_path, echec_commit=True)

    resultat = await _intervenir(tmp_path, chantier, _ecrire_un_ticket())

    assert resultat.statut == "blocked" and chantier.livraisons == [] and chantier.ferme
