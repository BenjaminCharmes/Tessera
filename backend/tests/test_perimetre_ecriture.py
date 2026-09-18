"""Un agent n'écrit que dans son projet — ticket-085."""
import json
from pathlib import Path

from vibe_ide.services.providers.perimetre import (
    ECRITURE_REFUS,
    hors_perimetre,
    hook_refus_hors_perimetre,
    racine_autorisee,
)


def _projet(tmp_path: Path, nom: str, agents: dict[str, object] | None = None) -> Path:
    racine = tmp_path / "projects" / nom
    racine.mkdir(parents=True, exist_ok=True)
    if agents is not None:
        (racine / "agents.json").write_text(
            json.dumps(agents), encoding="utf-8"
        )
    return racine


# ------------------------------------------------------------------
# Quelle racine un projet s'autorise
# ------------------------------------------------------------------


def test_par_defaut_la_racine_est_le_dossier_du_projet(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")

    assert racine_autorisee(projet) == projet.resolve()


def test_un_projet_qui_declare_ancestor_remonte_au_depot(tmp_path: Path) -> None:
    # ADR-028 : le projet bootstrap construit l'IDE, donc il écrit
    # volontairement au-dessus de lui, dans `backend/` et `frontend/`. La
    # racine est le **dépôt** qui le contient, pas `projects/`, qui ne veut
    # rien dire.
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, "ide-core", {"git_root": "ancestor"})

    assert racine_autorisee(projet) == tmp_path.resolve()


def test_une_valeur_inconnue_ne_desarme_rien(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client", {"git_root": "n'importe quoi"})

    assert racine_autorisee(projet) == projet.resolve()


def test_un_agents_json_illisible_ne_desarme_rien(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")
    (projet / "agents.json").write_text("{ pas du json", encoding="utf-8")

    assert racine_autorisee(projet) == projet.resolve()


# ------------------------------------------------------------------
# Ce qui est dedans, ce qui est dehors
# ------------------------------------------------------------------


def test_un_fichier_du_projet_passe(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")

    assert hors_perimetre(str(projet / "src" / "app.py"), projet) is False


def test_un_chemin_relatif_se_resout_depuis_la_racine(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")

    assert hors_perimetre("src/app.py", projet) is False
    assert hors_perimetre("../voisin/app.py", projet) is True


def test_le_projet_voisin_est_refuse(tmp_path: Path) -> None:
    # Le cas qui compte : six projets clients côte à côte dans `projects/`.
    # Un codeur qui se trompe de dossier écrit dans le dépôt d'un autre client.
    projet = _projet(tmp_path, "client-a")
    voisin = _projet(tmp_path, "client-b")

    assert hors_perimetre(str(voisin / "app.py"), projet) is True


def test_le_depot_de_vibe_ide_est_refuse(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")

    assert hors_perimetre(str(tmp_path / "backend" / "main.py"), projet) is True


def test_un_projet_ancestor_ecrit_dans_le_backend(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    projet = _projet(tmp_path, "ide-core", {"git_root": "ancestor"})

    assert hors_perimetre(str(tmp_path / "backend" / "main.py"), projet) is False


def test_le_dossier_personnel_est_refuse(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")

    assert hors_perimetre(str(Path.home() / ".ssh" / "config"), projet) is True


def test_un_nom_qui_commence_pareil_ne_passe_pas(tmp_path: Path) -> None:
    # `projects/client-a` ne doit pas ouvrir `projects/client-attaque` : une
    # comparaison de préfixe de chaîne laisserait passer.
    projet = _projet(tmp_path, "client-a")
    piege = _projet(tmp_path, "client-attaque")

    assert hors_perimetre(str(piege / "app.py"), projet) is True


# ------------------------------------------------------------------
# Le hook
# ------------------------------------------------------------------


async def test_le_hook_refuse_une_ecriture_hors_perimetre(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")
    voisin = _projet(tmp_path, "autre")
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(voisin / "x.py")}},
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert ECRITURE_REFUS[:30] in sortie["hookSpecificOutput"]["permissionDecisionReason"]


async def test_le_hook_laisse_passer_une_ecriture_du_projet(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Edit", "tool_input": {"file_path": str(projet / "x.py")}},
        None,
        None,
    )

    assert sortie == {}


async def test_le_hook_ignore_les_outils_de_lecture(tmp_path: Path) -> None:
    # Lire hors du projet reste permis : comprendre ce qui existe fait partie
    # du travail, et lire ne laisse pas de trace dans le dépôt de quelqu'un.
    projet = _projet(tmp_path, "client")
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}}, None, None
    )

    assert sortie == {}


async def test_sans_projet_le_hook_ne_contraint_rien(tmp_path: Path) -> None:
    # Les services texte→JSON tournent sans projet et sans outils : leur
    # imposer un périmètre n'aurait aucun sens.
    hook = hook_refus_hors_perimetre(None)

    sortie = await hook(
        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x"}}, None, None
    )

    assert sortie == {}


# ------------------------------------------------------------------
# Le hook est réellement posé sur les options du SDK
# ------------------------------------------------------------------


def test_les_options_portent_le_garde_d_ecriture(tmp_path: Path) -> None:
    # Un garde écrit mais jamais branché donne l'apparence d'une protection
    # sans en être une — c'est exactement ce qu'ADR-027 évitait avec les hooks.
    from vibe_ide.services.providers.agent_sdk import _build_options

    options = _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=tmp_path
    )

    matchers = options.hooks["PreToolUse"]
    couverts = {m.matcher for m in matchers}
    assert "Bash" in couverts
    assert "Write|Edit|NotebookEdit|Bash" in couverts


# ------------------------------------------------------------------
# Les redirections shell évidentes — ticket-088
# ------------------------------------------------------------------


def test_une_redirection_hors_perimetre_est_vue(tmp_path: Path) -> None:
    from vibe_ide.services.providers.perimetre import cibles_ecrites

    projet = _projet(tmp_path, "client")

    assert cibles_ecrites("echo x > ../voisin/app.py") == ["../voisin/app.py"]
    assert cibles_ecrites("cat a >> /etc/hosts") == ["/etc/hosts"]
    assert cibles_ecrites("make | tee ../ailleurs/log.txt") == ["../ailleurs/log.txt"]
    assert projet.exists()


def test_une_commande_sans_ecriture_ne_donne_aucune_cible() -> None:
    from vibe_ide.services.providers.perimetre import cibles_ecrites

    assert cibles_ecrites("uv run pytest -q") == []
    assert cibles_ecrites("grep -r 'x > y' src/") == []


def test_une_redirection_de_flux_n_est_pas_un_fichier() -> None:
    # `2>&1` et `> /dev/null` sont partout dans les commandes de test.
    from vibe_ide.services.providers.perimetre import cibles_ecrites

    assert cibles_ecrites("pytest 2>&1") == []
    assert cibles_ecrites("pytest > /dev/null") == []


async def test_le_hook_refuse_un_bash_qui_ecrit_dehors(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")
    _projet(tmp_path, "voisin")
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": "echo x > ../voisin/app.py"}},
        None,
        None,
    )

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_le_hook_laisse_passer_un_bash_qui_ecrit_dedans(tmp_path: Path) -> None:
    projet = _projet(tmp_path, "client")
    hook = hook_refus_hors_perimetre(projet)

    sortie = await hook(
        {"tool_name": "Bash", "tool_input": {"command": "uv run pytest -q > out.txt"}},
        None,
        None,
    )

    assert sortie == {}


async def test_le_hook_laisse_passer_une_commande_de_test(tmp_path: Path) -> None:
    # Le coût d'un faux refus est élevé : l'agent perd son moyen de vérifier
    # son propre travail, et le ticket part en revue sans avoir tourné.
    projet = _projet(tmp_path, "client")
    hook = hook_refus_hors_perimetre(projet)

    for commande in ("uv run pytest -q", "npm test 2>&1", "npx tsc --noEmit"):
        assert await hook(
            {"tool_name": "Bash", "tool_input": {"command": commande}}, None, None
        ) == {}, commande
