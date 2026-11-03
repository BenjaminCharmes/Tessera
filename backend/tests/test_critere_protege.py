"""Un critère qui exige un fichier protégé arrête le run avant le codeur — ticket-476."""
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult
from tessera.models.ticket import TicketStatus
from tessera.services.critere_protege import (
    critere_demande_ecriture,
    criteres_sur_chemins_proteges,
)
from tessera.services.orchestrator import Orchestrator
from tests.test_orchestrator import (
    _FakeGit,
    _RecordingRunner,
    _make_orchestrator,
    _make_ticket,
    _noop,
)


def _chemin(critere: str, tmp_path: Path) -> str | None:
    return critere_demande_ecriture(critere, tmp_path, tmp_path)


# ------------------------------------------------------------------
# La règle de détection
# ------------------------------------------------------------------


def test_un_critere_qui_dit_ce_que_contient_claude_md_est_retenu(tmp_path: Path) -> None:
    assert _chemin("`CLAUDE.md` contient la nouvelle section", tmp_path) == "CLAUDE.md"


def test_un_critere_qui_cite_claude_md_pour_le_lire_n_est_pas_retenu(tmp_path: Path) -> None:
    assert _chemin("Le code ajoute une section, d'après `CLAUDE.md`", tmp_path) is None
    assert _chemin("Le chargeur lit `CLAUDE.md` et renvoie son titre", tmp_path) is None


def test_un_verbe_loin_du_chemin_ne_suffit_pas(tmp_path: Path) -> None:
    critere = (
        "Ajouter une section détaillée sur la politique de nommage des fichiers "
        "du projet et confirmer le chargement de `CLAUDE.md`"
    )
    assert _chemin(critere, tmp_path) is None


def test_un_verbe_d_une_autre_proposition_ne_suffit_pas(tmp_path: Path) -> None:
    assert _chemin("Ajouter. Le chargeur renvoie `CLAUDE.md`", tmp_path) is None


def test_une_negation_n_est_pas_une_demande_d_ecriture(tmp_path: Path) -> None:
    assert _chemin("Ne pas modifier `CLAUDE.md`", tmp_path) is None


def test_un_chemin_non_protege_n_est_pas_retenu(tmp_path: Path) -> None:
    assert _chemin("`src/app.py` modifié pour gérer le cas vide", tmp_path) is None


def test_un_skill_cree_est_retenu(tmp_path: Path) -> None:
    critere = "`.claude/skills/x/SKILL.md` créé avec une description"
    assert _chemin(critere, tmp_path) == ".claude/skills/x/SKILL.md"


def test_un_workflow_de_ci_a_modifier_est_retenu(tmp_path: Path) -> None:
    critere = "Modifier `.github/workflows/ci.yml` pour lancer les tests"
    assert _chemin(critere, tmp_path) == ".github/workflows/ci.yml"


def test_un_jeton_avec_numero_de_ligne_est_une_lecture(tmp_path: Path) -> None:
    assert _chemin("Corriger le bug décrit en `CLAUDE.md:12`", tmp_path) is None


def test_un_critere_qui_decrit_un_test_n_est_pas_retenu(tmp_path: Path) -> None:
    # Le livrable est un test : `agents.json` n'est que la donnée qu'il lit.
    critere = (
        "Un test vérifie que `ProjectOverview.online_declared` vaut `true` pour "
        "un projet dont `agents.json` déclare `online`, et `false` sinon"
    )
    assert _chemin(critere, tmp_path) is None
    assert _chemin("Un test vérifie que `agents.json` déclare le port", tmp_path) is None


def test_un_projet_dont_agents_json_declare_est_une_condition(tmp_path: Path) -> None:
    assert _chemin("Pour un projet dont `agents.json` déclare `online`", tmp_path) is None


def test_un_chemin_cite_entre_guillemets_n_est_pas_retenu(tmp_path: Path) -> None:
    critere = "Le contrôle refuse un critère qui dit « `CLAUDE.md` contient la section »"
    assert _chemin(critere, tmp_path) is None


def test_ce_que_le_code_livre_ecrit_n_est_pas_un_livrable_du_run(tmp_path: Path) -> None:
    # L'analyseur de projet écrit un `CLAUDE.md` chez l'utilisateur : le run
    # n'a pas à en écrire un lui-même.
    assert _chemin("L'analyseur crée `CLAUDE.md` à l'import du projet", tmp_path) is None
    assert _chemin("Le gabarit écrit `CLAUDE.md` dans le projet neuf", tmp_path) is None


def test_un_nom_d_action_ou_un_participe_avant_le_chemin_est_retenu(tmp_path: Path) -> None:
    assert _chemin("Ajout d'une section Règles dans `CLAUDE.md`", tmp_path) == "CLAUDE.md"
    assert _chemin("La section Règles est ajoutée à `CLAUDE.md`", tmp_path) == "CLAUDE.md"
    assert _chemin("Mettre à jour `CLAUDE.md` avec la commande", tmp_path) == "CLAUDE.md"


def test_un_fichier_genere_ou_cree_par_le_code_livre_n_est_pas_un_livrable(
    tmp_path: Path,
) -> None:
    assert _chemin("Le `CLAUDE.md` généré contient les agents recommandés", tmp_path) is None
    critere = "Un projet créé par `POST /projects` contient un `.git` à sa racine"
    assert _chemin(critere, tmp_path) is None


def test_un_verbe_apres_une_liaison_n_est_pas_celui_du_chemin(tmp_path: Path) -> None:
    assert _chemin("Le service génère `CLAUDE.md` et ajoute un résumé", tmp_path) is None


def test_la_liste_donne_le_numero_du_critere(tmp_path: Path) -> None:
    criteres = ["Le code compile", "`agents.json` déclare le nouveau service"]
    retenus = criteres_sur_chemins_proteges(criteres, tmp_path, tmp_path)
    assert retenus == [(2, "agents.json")]


# ------------------------------------------------------------------
# L'arrêt avant le codeur
# ------------------------------------------------------------------


class _CodeurInterdit:
    """Runner qui échoue s'il est appelé : l'arrêt doit précéder le codeur."""

    def __init__(self) -> None:
        self.appels = 0

    async def run(self, **kwargs: object) -> AgentResult:
        self.appels += 1
        raise AssertionError("le codeur ne doit pas être appelé")


def _orchestrateur(
    tmp_path: Path, critere: str, runner: object, git: _FakeGit
) -> Orchestrator:
    ticket = _make_ticket(body=f"## Critères d'acceptation\n- [ ] {critere}\n")
    service = AsyncMock()
    service.get_ticket.return_value = ticket
    return _make_orchestrator(
        tmp_path, runner=runner, ticket_service=service,  # type: ignore[arg-type]
        git_workspace=git, project_path=tmp_path,
    )


async def test_un_critere_sur_claude_md_arrete_le_run_avant_le_codeur(tmp_path: Path) -> None:
    runner, git = _CodeurInterdit(), _FakeGit()
    orch = _orchestrateur(tmp_path, "`CLAUDE.md` contient la nouvelle section", runner, git)

    result = await orch.run_pipeline("projet", "ticket-001", _noop)

    assert runner.appels == 0
    assert result.final_status is TicketStatus.blocked
    assert result.approved is False
    assert result.arret is not None and "CLAUDE.md" in result.arret
    assert "critère 1" in result.arret
    assert len(git.commits) == 1


async def test_un_critere_qui_cite_claude_md_sans_l_ecrire_appelle_le_codeur(
    tmp_path: Path,
) -> None:
    runner = _RecordingRunner()
    critere = "Le code suit les règles d'après `CLAUDE.md`"
    orch = _orchestrateur(tmp_path, critere, runner, _FakeGit())

    await orch.run_pipeline("projet", "ticket-001", _noop)

    roles = [appel["role"].value for appel in runner.calls]  # type: ignore[attr-defined]
    assert "codeur" in roles
