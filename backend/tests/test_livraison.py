"""Livrer un run aussi loin que le projet le déclare — ticket-083."""
import json
from pathlib import Path

from tessera.services.livraison import LivraisonService, Livraison


class _FauxGit:
    def __init__(
        self, conflits: tuple[str, ...] = (), resolvables: bool = False
    ) -> None:
        self._conflits = conflits
        self._resolvables = resolvables
        self.rejoue: list[str] = []
        self.syncs: list[str] = []

    async def rejouer_sur(self, base, resolveur=None):  # type: ignore[no-untyped-def]
        self.rejoue.append(base)
        if self._conflits and resolveur is not None and self._resolvables:
            await resolveur(self._conflits)
            return ()
        return self._conflits

    async def sync_base_depuis_distant(self, base_branch: str) -> str | None:
        self.syncs.append(base_branch)
        return None


class _FauxWorkflow:
    def __init__(self, ci: list[str] | None = None, merge: bool = True) -> None:
        self.ouvertures: list[dict[str, object]] = []
        self.merges: list[int] = []
        self._ci = list(ci or ["passing"])
        self._merge = merge

    async def open_pull_request(self, **kwargs: object) -> object:
        self.ouvertures.append(kwargs)

        class _R:
            pr_number = 7
            pr_url = "https://github.com/o/r/pull/7"
            branch = "ticket-001-x"

        return _R()

    async def etat_ci(self, pr_number: int) -> str:
        return self._ci.pop(0) if len(self._ci) > 1 else self._ci[0]

    async def merge_si_la_ci_est_verte(self, pr_number: int) -> bool:
        self.merges.append(pr_number)
        return self._merge


def _projet(tmp_path: Path, niveau: str | None) -> Path:
    racine = tmp_path / (niveau or "rien")
    racine.mkdir(parents=True, exist_ok=True)
    if niveau is not None:
        (racine / "agents.json").write_text(
            json.dumps({"autonomy": niveau}), encoding="utf-8"
        )
    return racine


def _service(
    tmp_path: Path,
    niveau: str | None,
    git: _FauxGit | None = None,
    workflow: _FauxWorkflow | None = None,
    resolveur: object | None = None,
) -> tuple[LivraisonService, _FauxGit, _FauxWorkflow]:
    g = git or _FauxGit()
    w = workflow or _FauxWorkflow()
    svc = LivraisonService(
        git_workspace=g,
        workflow=w,
        project_path=_projet(tmp_path, niveau),
        base_branch="develop",
        attente_ci_max_s=0,
        dormir=_ne_dort_pas,
        resolveur=resolveur,  # type: ignore[arg-type]
    )
    return svc, g, w


async def _ne_dort_pas(_secondes: float) -> None:
    return None


async def _livrer(svc: LivraisonService, approuve: bool = True) -> Livraison:
    return await svc.livrer(
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        branch="ticket-001-x",
        approuve=approuve,
    )


async def test_un_run_non_approuve_ne_se_livre_pas(tmp_path: Path) -> None:
    # ADR-018 : un run rejeté commite quand même, sous `chore: … unapproved
    # work`. Livrer ce commit reviendrait à pousser un travail que le reviewer
    # a refusé.
    svc, git, workflow = _service(tmp_path, "merge")

    livraison = await _livrer(svc, approuve=False)

    assert workflow.ouvertures == []
    assert git.rejoue == []
    assert "approuv" in (livraison.arret or "")


async def test_un_projet_en_commit_s_arrete_apres_le_commit(tmp_path: Path) -> None:
    svc, git, workflow = _service(tmp_path, "commit")

    livraison = await _livrer(svc)

    assert workflow.ouvertures == []
    assert git.rejoue == []
    assert livraison.arret is not None
    assert "agents.json" in livraison.arret


async def test_un_conflit_arrete_la_livraison_et_nomme_les_fichiers(
    tmp_path: Path,
) -> None:
    # Pousser une branche qui ne rejoue pas sur sa base produit une PR que
    # GitHub declare non mergeable : attendre sa CI ne mene nulle part.
    svc, _git, workflow = _service(
        tmp_path, "merge", git=_FauxGit(conflits=("src/app.py",))
    )

    livraison = await _livrer(svc)

    assert livraison.conflits == ("src/app.py",)
    assert workflow.ouvertures == []
    assert "src/app.py" in (livraison.arret or "")


async def test_un_projet_en_pr_ouvre_et_s_arrete_la(tmp_path: Path) -> None:
    svc, git, workflow = _service(tmp_path, "pr")

    livraison = await _livrer(svc)

    assert git.rejoue == ["develop"]
    assert livraison.pr_number == 7
    assert workflow.merges == []
    assert livraison.merged is False
    assert livraison.arret is None


async def test_livraison_transmet_le_type_du_ticket(tmp_path: Path) -> None:
    # ticket-259 : LivraisonService doit transmettre ticket_type à
    # open_pull_request pour que le titre de la PR soit Conventional Commits.
    svc, _git, workflow = _service(tmp_path, "pr")

    await svc.livrer(
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        ticket_type="feat",
        branch="ticket-001-x",
        approuve=True,
    )

    assert len(workflow.ouvertures) == 1
    assert workflow.ouvertures[0]["ticket_type"] == "feat"


async def test_un_projet_en_merge_va_jusqu_au_bout(tmp_path: Path) -> None:
    svc, _git, workflow = _service(tmp_path, "merge")

    livraison = await _livrer(svc)

    assert livraison.pr_number == 7
    assert workflow.merges == [7]
    assert livraison.merged is True
    assert livraison.arret is None


async def test_une_ci_qui_echoue_laisse_la_pr_ouverte(tmp_path: Path) -> None:
    # Le travail n'est pas perdu : la PR reste là, et l'utilisateur voit
    # pourquoi elle n'a pas été mergée.
    svc, _git, workflow = _service(
        tmp_path, "merge", workflow=_FauxWorkflow(ci=["failing"], merge=False)
    )

    livraison = await _livrer(svc)

    assert livraison.pr_number == 7
    assert livraison.merged is False
    assert "CI" in (livraison.arret or "")


async def test_une_ci_qui_ne_repond_jamais_n_attend_pas_indefiniment(
    tmp_path: Path,
) -> None:
    # Une attente sans borne bloquerait la file de tickets, et ADR-018 fait
    # reposer le ticket suivant sur un arbre propre.
    svc, _git, workflow = _service(
        tmp_path, "merge", workflow=_FauxWorkflow(ci=["pending"], merge=False)
    )

    livraison = await _livrer(svc)

    assert livraison.pr_number == 7
    assert livraison.merged is False
    assert workflow.merges == []
    assert "attente" in (livraison.arret or "").lower()


async def test_la_ci_verte_arrive_apres_quelques_tours(tmp_path: Path) -> None:
    svc, _git, workflow = _service(
        tmp_path,
        "merge",
        workflow=_FauxWorkflow(ci=["pending", "pending", "passing"]),
    )
    svc._attente_ci_max_s = 60

    livraison = await _livrer(svc)

    assert livraison.merged is True


async def test_les_etapes_racontent_ce_qui_a_ete_fait(tmp_path: Path) -> None:
    svc, _git, _workflow = _service(tmp_path, "merge")

    livraison = await _livrer(svc)

    assert "rebase" in " ".join(livraison.etapes).lower()
    assert any("7" in e for e in livraison.etapes)


# ------------------------------------------------------------------
# Un conflit résolu se relit toujours — ticket-090
# ------------------------------------------------------------------


async def test_un_conflit_resolu_laisse_la_livraison_continuer(
    tmp_path: Path,
) -> None:
    appels: list[tuple[str, ...]] = []

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)

    svc, _git, workflow = _service(
        tmp_path,
        "merge",
        git=_FauxGit(conflits=("src/app.py",), resolvables=True),
        resolveur=resoudre,
    )

    livraison = await _livrer(svc)

    assert appels == [("src/app.py",)]
    assert livraison.pr_number == 7
    assert livraison.conflits == ("src/app.py",)


async def test_un_conflit_resolu_n_est_jamais_merge_seul(tmp_path: Path) -> None:
    # Un conflit est par définition l'endroit où deux intentions divergent.
    # C'est le pire endroit pour deviner — et le projet a beau déclarer
    # `merge`, il n'a pas déclaré ça.
    async def resoudre(fichiers: tuple[str, ...]) -> None:
        return None

    svc, _git, workflow = _service(
        tmp_path,
        "merge",
        git=_FauxGit(conflits=("src/app.py",), resolvables=True),
        resolveur=resoudre,
    )

    livraison = await _livrer(svc)

    assert workflow.merges == []
    assert livraison.merged is False
    assert "conflit" in (livraison.arret or "").lower()
    assert "relire" in (livraison.arret or "").lower()


async def test_sans_conflit_le_resolveur_ne_change_rien(tmp_path: Path) -> None:
    async def resoudre(fichiers: tuple[str, ...]) -> None:
        raise AssertionError("ne doit pas être appelé")

    svc, _git, workflow = _service(tmp_path, "merge", resolveur=resoudre)

    livraison = await _livrer(svc)

    assert livraison.merged is True
    assert livraison.conflits == ()


async def test_un_conflit_non_resolu_arrete_toujours_tout(tmp_path: Path) -> None:
    async def resoudre(fichiers: tuple[str, ...]) -> None:
        return None

    svc, _git, workflow = _service(
        tmp_path,
        "merge",
        git=_FauxGit(conflits=("src/app.py",), resolvables=False),
        resolveur=resoudre,
    )

    livraison = await _livrer(svc)

    assert workflow.ouvertures == []
    assert livraison.conflits == ("src/app.py",)


# ------------------------------------------------------------------
# Délai de grâce avant de lire none comme verdict — ticket-260
# ------------------------------------------------------------------


def _service_avec_grace(
    tmp_path: Path,
    ci: list[str],
    grace_ci_s: float = 20.0,
    attente_ci_max_s: float = 60.0,
    intervalle_ci_s: float = 10.0,
) -> tuple[LivraisonService, _FauxWorkflow]:
    """Service en mode `merge` avec paramètres de grâce configurables."""
    racine = tmp_path / "projet_grace"
    racine.mkdir(parents=True, exist_ok=True)
    (racine / "agents.json").write_text(
        json.dumps({"autonomy": "merge"}), encoding="utf-8"
    )
    w = _FauxWorkflow(ci=ci)
    svc = LivraisonService(
        git_workspace=_FauxGit(),
        workflow=w,
        project_path=racine,
        base_branch="develop",
        attente_ci_max_s=attente_ci_max_s,
        intervalle_ci_s=intervalle_ci_s,
        grace_ci_s=grace_ci_s,
        dormir=_ne_dort_pas,
    )
    return svc, w


async def test_none_puis_passing_dans_le_delai_de_grace_merge(
    tmp_path: Path,
) -> None:
    # GitHub n'enregistre les checks qu'après l'ouverture de la PR.  Un
    # premier poll renvoie `none` avant qu'aucun check n'existe.  La livraison
    # doit continuer d'attendre pendant le délai de grâce et merger quand la
    # CI passe au vert.
    svc, workflow = _service_avec_grace(tmp_path, ci=["none", "passing"])

    livraison = await _livrer(svc)

    assert livraison.merged is True
    assert workflow.merges == [7]


async def test_none_persistant_apres_le_delai_de_grace_arrete_la_livraison(
    tmp_path: Path,
) -> None:
    # Passé le délai de grâce, `none` redevient un verdict final : l'absence
    # de signal n'est pas un signal favorable (ADR-029).
    svc, workflow = _service_avec_grace(tmp_path, ci=["none"])

    livraison = await _livrer(svc)

    assert livraison.merged is False
    assert workflow.merges == []
    assert "none" in (livraison.arret or "")


async def test_failing_pendant_le_delai_de_grace_arrete_immediatement(
    tmp_path: Path,
) -> None:
    # `failing` est un verdict définitif : la livraison s'arrête sans
    # attendre la fin du délai de grâce.
    svc, workflow = _service_avec_grace(tmp_path, ci=["failing"])

    livraison = await _livrer(svc)

    assert livraison.merged is False
    assert workflow.merges == []
    assert "CI" in (livraison.arret or "")


# ------------------------------------------------------------------
# Livraison aligne la base sur le distant avant le rebase — ticket-285
# ------------------------------------------------------------------


async def test_livraison_sync_base_avant_rebase(tmp_path: Path) -> None:
    """Livraison calls sync_base_depuis_distant before rejoyer_sur (ticket-285).

    The rebase in livraison must happen on the remote-synced base, not on
    whatever the local branch currently points to.
    """
    git = _FauxGit()
    svc, g, _w = _service(tmp_path, "pr", git=git)

    await _livrer(svc)

    # sync must have been called, and before the rebase
    assert g.syncs == ["develop"], (
        "sync_base_depuis_distant must be called once with the base branch"
    )
    assert g.rejoue == ["develop"], "rejoyer_sur must follow the sync"
