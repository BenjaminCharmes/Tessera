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
    assert "Write|Edit|NotebookEdit" in couverts
