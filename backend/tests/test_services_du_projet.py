"""Lancer les services déclarés d'un projet — ticket-137.

ADR-042 : la commande se **déclare**, elle ne se devine pas. Les projets
décrivent leur démarrage dans des sections aux noms différents, mêlé aux
commandes de test et d'installation ; y choisir, c'est deviner. Et c'est le
backend qui lance, sans shell et sans agent — confier `Bash` à un agent pour
ça rouvrirait ce qu'ADR-027 et ADR-031 ferment mal.

Un serveur ne se termine jamais : c'est ce qui sépare ces tests de ceux de
`TestRunnerService`, qui attend la fin de sa commande.
"""
import asyncio
import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.process_registry import PROCESS_REGISTRY

#: Un « service » qui vit assez longtemps pour être observé puis arrêté, sans
#: dépendre de rien d'installé sur la machine de test.
_DORMEUR = f'"{sys.executable}" -c "import time; time.sleep(30)"'
_BAVARD = (
    f'"{sys.executable}" -c '
    '"import sys; print(\'je suis la\', flush=True); '
    "import time; time.sleep(30)\""
)


def _manifeste(project: Path, services: list[dict[str, str]]) -> None:
    project.joinpath("agents.json").write_text(
        json.dumps({"project_id": project.name, "services": services}),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for project_id in ("mon-projet", "sans-services"):
        project = ws / project_id
        (project / "memory").mkdir(parents=True)
        (project / "CLAUDE.md").write_text(f"# {project_id}\n", encoding="utf-8")
        for status in ("todo", "in-progress", "in-review", "done", "blocked"):
            (project / "tickets" / status).mkdir(parents=True)
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


@pytest.fixture(autouse=True)
def _arreter_tout() -> Iterator[None]:
    yield
    asyncio.run(PROCESS_REGISTRY.tout_arreter())


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _demarrer(client: TestClient, project_id: str) -> dict:
    return client.post(f"/api/v1/projects/{project_id}/services/start").json()


# --------------------------------------------------------------------------
# Le manifeste
# --------------------------------------------------------------------------


def test_un_projet_sans_services_refuse_et_dit_quoi_declarer(
    client: TestClient,
) -> None:
    # Le défaut protège (ADR-042) : rien de déclaré, pas de lancement. Mais un
    # refus qui ne dit pas quoi écrire envoie lire le code.
    resp = client.post("/api/v1/projects/sans-services/services/start")

    assert resp.status_code == 409
    assert "services" in resp.json()["detail"]


def test_un_service_declare_demarre_et_porte_son_pid(
    client: TestClient, workspace: Path
) -> None:
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])

    demarrage = _demarrer(client, "mon-projet")
    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert [s["nom"] for s in demarrage["services"]] == ["api"]
    assert listing[0]["nom"] == "api"
    assert isinstance(listing[0]["pid"], int) and listing[0]["pid"] > 0
    assert listing[0]["en_cours"] is True


def test_deux_services_demarrent_ensemble(
    client: TestClient, workspace: Path
) -> None:
    # `orion-backend` veut uvicorn **et** un worker Celery : l'heuristique « un
    # fichier, une commande » ne couvrait pas ce cas.
    _manifeste(
        workspace / "mon-projet",
        [
            {"nom": "api", "commande": _DORMEUR},
            {"nom": "worker", "commande": _DORMEUR},
        ],
    )

    _demarrer(client, "mon-projet")
    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert sorted(s["nom"] for s in listing) == ["api", "worker"]


def test_arreter_termine_le_processus_et_le_retire(
    client: TestClient, workspace: Path
) -> None:
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    _demarrer(client, "mon-projet")

    client.post("/api/v1/projects/mon-projet/services/stop")
    listing = client.get("/api/v1/projects/mon-projet/services").json()

    # Le service reste **déclaré**, donc listé, mais plus lancé : c'est ce
    # qui permet au bouton de rester en place et de proposer « Lancer »
    # (ticket-146). Une liste vide le ferait disparaître.
    assert [s["nom"] for s in listing] == ["api"]
    assert listing[0]["en_cours"] is False
    assert listing[0]["pid"] is None


# --------------------------------------------------------------------------
# Ce que la commande n'a pas le droit d'être
# --------------------------------------------------------------------------


def test_la_commande_n_est_pas_passee_a_un_shell(
    client: TestClient, workspace: Path
) -> None:
    # Sans shell, `&&` n'enchaîne rien : il arrive tel quel en argument. Le
    # refuser tôt vaut mieux que de lancer une commande amputée qui écoute un
    # port sans qu'on comprenne pourquoi.
    _manifeste(
        workspace / "mon-projet",
        [{"nom": "api", "commande": "echo un && echo deux"}],
    )

    resp = client.post("/api/v1/projects/mon-projet/services/start")

    assert resp.status_code == 422
    assert "shell" in resp.json()["detail"].lower()


def test_un_cwd_hors_du_projet_est_refuse(
    client: TestClient, workspace: Path
) -> None:
    # Même frontière qu'ADR-031 : ce que l'IDE lance ne travaille pas chez le
    # voisin. Six dépôts clients côte à côte dans `projects/`, et un `cwd`
    # mal écrit démarre un serveur dans le mauvais.
    _manifeste(
        workspace / "mon-projet",
        [{"nom": "api", "commande": _DORMEUR, "cwd": "../sans-services"}],
    )

    resp = client.post("/api/v1/projects/mon-projet/services/start")

    assert resp.status_code == 422
    # « périmètre » et non « racine » : depuis ticket-143 la frontière peut
    # être le dépôt qui contient le projet, quand celui-ci le déclare.
    assert "périmètre" in resp.json()["detail"].lower()


# --------------------------------------------------------------------------
# Ce que le service écrit
# --------------------------------------------------------------------------


def test_la_sortie_du_service_part_sur_le_canal(
    client: TestClient, workspace: Path
) -> None:
    # Le canal d'ADR-041 porte « ce que l'IDE est en train de faire » : un
    # serveur qui tourne en fait partie.
    from tessera.services.event_hub import EVENT_HUB
    from tessera.services.pipeline_events import EventType

    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _BAVARD}])
    abonne = EVENT_HUB.subscribe()
    try:
        _demarrer(client, "mon-projet")
        recus: list[object] = []
        for _ in range(40):
            recus = abonne.vider()
            if any(e.type is EventType.SERVICE_OUTPUT for e in recus):  # type: ignore[attr-defined]
                break
            asyncio.run(asyncio.sleep(0.1))
    finally:
        abonne.fermer()

    lignes = [
        e.data.get("ligne")  # type: ignore[attr-defined]
        for e in recus
        if e.type is EventType.SERVICE_OUTPUT  # type: ignore[attr-defined]
    ]
    assert any("je suis la" in str(ligne) for ligne in lignes), recus


def test_les_services_sont_arretes_avec_le_backend(
    client: TestClient, workspace: Path
) -> None:
    # L'alternative qu'ADR-042 rejette : un processus détaché survivrait à
    # l'IDE en gardant son port, sans rien pour l'arrêter. Ce test est ce qui
    # empêche ce choix de revenir par accident.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    _demarrer(client, "mon-projet")
    pids = [s.pid for s in PROCESS_REGISTRY.services_de("mon-projet")]
    assert pids

    asyncio.run(PROCESS_REGISTRY.tout_arreter())

    assert PROCESS_REGISTRY.services_de("mon-projet") == []


def test_un_operateur_dans_un_argument_cite_reste_permis() -> None:
    # Le piège payé en écrivant ce ticket : une recherche naïve de « ; » dans
    # la chaîne entière refusait `python -c "import time; time.sleep(30)"`,
    # où le point-virgule appartient au code Python, pas au shell. Le contrôle
    # porte sur les tokens après découpage.
    from tessera.services.process_registry import verifier_la_commande

    args = verifier_la_commande('python -c "import time; time.sleep(30)"')

    assert args == ["python", "-c", "import time; time.sleep(30)"]


def test_un_operateur_isole_reste_refuse() -> None:
    # Le pendant : sans lui, alléger le contrôle laisserait passer une ligne
    # de shell entière, dont seule la première moitié serait lancée.
    from tessera.services.process_registry import (
        CommandeInvalide,
        verifier_la_commande,
    )

    for ligne in ("npm run dev && npm run api", "uvicorn app:app | tee log"):
        with pytest.raises(CommandeInvalide):
            verifier_la_commande(ligne)


# --------------------------------------------------------------------------
# Le dépôt ancêtre — ticket-143
# --------------------------------------------------------------------------


def _racine_et_projet(tmp_path: Path, git_root: str | None) -> tuple[Path, Path]:
    """Un dépôt qui contient un projet, comme Tessera contient `ide-core`."""
    depot = tmp_path / "depot"
    (depot / ".git").mkdir(parents=True)
    (depot / "backend").mkdir()
    projet = depot / "projects" / "mon-projet"
    projet.mkdir(parents=True)
    manifeste: dict[str, object] = {"project_id": "mon-projet"}
    if git_root is not None:
        manifeste["git_root"] = git_root
    projet.joinpath("agents.json").write_text(
        json.dumps(manifeste), encoding="utf-8"
    )
    return depot, projet


def test_sans_declaration_le_cwd_reste_enferme(tmp_path: Path) -> None:
    # Le défaut protège : six dépôts clients côte à côte, et un `cwd` mal
    # écrit démarre un serveur chez le voisin.
    from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd

    _, projet = _racine_et_projet(tmp_path, git_root=None)

    with pytest.raises(CommandeInvalide):
        resoudre_le_cwd(projet, "../../backend")


def test_git_root_ancestor_ouvre_le_depot_qui_contient(tmp_path: Path) -> None:
    # ADR-028 : le projet bootstrap construit l'IDE, donc il travaille
    # volontairement au-dessus de lui, dans `backend/` et `frontend/`. Sans
    # cette exception, `ide-core` ne pourrait pas lancer ses propres services.
    from tessera.services.process_registry import resoudre_le_cwd

    depot, projet = _racine_et_projet(tmp_path, git_root="ancestor")

    assert resoudre_le_cwd(projet, "../../backend") == (depot / "backend").resolve()


def test_une_valeur_inconnue_de_git_root_ne_desarme_rien(tmp_path: Path) -> None:
    # Élargir un périmètre est le geste qui se relit le moins bien : seule la
    # valeur exacte compte, comme pour ADR-021 et ADR-023.
    from tessera.services.process_registry import CommandeInvalide, resoudre_le_cwd

    _, projet = _racine_et_projet(tmp_path, git_root="parent")

    with pytest.raises(CommandeInvalide):
        resoudre_le_cwd(projet, "../../backend")


def test_un_executable_introuvable_dit_quoi_essayer() -> None:
    # Sans shell, `npm` n'existe pas sous Windows — c'est `npm.cmd`. L'erreur
    # brute « fichier introuvable » n'aide personne à le deviner, et c'est le
    # prix assumé de ne pas passer par un shell (ADR-042).
    import os

    from tessera.services.process_registry import introuvable

    message = introuvable("npm")

    assert "npm" in message
    if os.name == "nt":
        assert "npm.cmd" in message
    # Un programme déjà nommé complètement n'a pas besoin du conseil.
    assert ".cmd" not in introuvable("npm.cmd").replace("npm.cmd", "", 1)


def test_npm_se_lance_sans_ecrire_cmd_dans_le_manifeste(
    client: TestClient, workspace: Path
) -> None:
    # `agents.json` est versionné et part sur d'autres machines : y écrire
    # « npm.cmd » ferait un manifeste qui ne marche que sous Windows. C'est
    # le lancement qui s'adapte, pas le fichier partagé.
    import shutil

    if shutil.which("npm") is None and shutil.which("npm.cmd") is None:
        pytest.skip("npm absent de cette machine")

    _manifeste(
        workspace / "mon-projet", [{"nom": "front", "commande": "npm --version"}]
    )

    resp = client.post("/api/v1/projects/mon-projet/services/start")

    assert resp.status_code == 200, resp.text


# --------------------------------------------------------------------------
# Un service mort reste visible — ticket-144
# --------------------------------------------------------------------------

_QUI_MEURT = f'"{sys.executable}" -c "import sys; sys.exit(3)"'


def _attendre_la_fin(client: TestClient, nom: str, limite: int = 60) -> dict:
    """Relit jusqu'à ce que le service ne soit plus en cours."""
    import time

    for _ in range(limite):
        listing = client.get("/api/v1/projects/mon-projet/services").json()
        trouve = [s for s in listing if s["nom"] == nom]
        if trouve and not trouve[0]["en_cours"]:
            return trouve[0]
        time.sleep(0.1)
    raise AssertionError(f"« {nom} » toujours en cours, ou disparu : {listing}")


def test_un_service_mort_seul_reste_dans_la_liste(
    client: TestClient, workspace: Path
) -> None:
    # Trouvé au premier essai réel : le backend d'ide-core mourait sur un port
    # déjà pris et **disparaissait** au lieu de s'afficher en échec. Vu de
    # l'IDE, le lancement paraissait à moitié réussi, sans rien dire du reste.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _QUI_MEURT}])
    _demarrer(client, "mon-projet")

    mort = _attendre_la_fin(client, "api")

    assert mort["en_cours"] is False
    assert mort["code_de_sortie"] == 3


def test_relancer_apres_un_echec_ne_laisse_qu_une_entree(
    client: TestClient, workspace: Path
) -> None:
    # Garder les morts ne doit pas faire grossir la liste à chaque clic.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _QUI_MEURT}])
    _demarrer(client, "mon-projet")
    _attendre_la_fin(client, "api")

    _demarrer(client, "mon-projet")
    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert len([s for s in listing if s["nom"] == "api"]) == 1


def test_un_service_arrete_a_la_main_n_est_pas_un_echec(
    client: TestClient, workspace: Path
) -> None:
    # `terminate()` produit un code non nul sur certaines plateformes :
    # afficher un échec là où l'utilisateur vient de cliquer « Arrêter »
    # enverrait chercher des logs qui ne disent rien.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    _demarrer(client, "mon-projet")

    client.post("/api/v1/projects/mon-projet/services/stop")
    listing = client.get("/api/v1/projects/mon-projet/services").json()

    # Arrêté à la main : ni « en cours », ni en échec. Il n'a pas échoué.
    assert listing[0]["en_cours"] is False
    assert listing[0]["code_de_sortie"] is None


def test_la_fin_d_un_service_est_annoncee(
    client: TestClient, workspace: Path
) -> None:
    # Sans annonce, l'écran ne peut apprendre la mort d'un service qu'en
    # sondant en boucle : il afficherait « en cours » pour un processus qui
    # n'existe plus (ticket-145).
    from tessera.services.event_hub import EVENT_HUB
    from tessera.services.pipeline_events import EventType

    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _QUI_MEURT}])
    abonne = EVENT_HUB.subscribe()
    try:
        _demarrer(client, "mon-projet")
        _attendre_la_fin(client, "api")
        recus = abonne.vider()
    finally:
        abonne.fermer()

    fins = [e for e in recus if e.type is EventType.SERVICE_CLOSED]
    assert fins, [e.type for e in recus]
    assert fins[0].data["service"] == "api"
    assert fins[0].data["code_de_sortie"] == 3
    assert fins[0].project_id == "mon-projet"


# --------------------------------------------------------------------------
# Connaître les services déclarés avant le clic — ticket-146
# --------------------------------------------------------------------------


def test_les_services_declares_sont_listes_avant_tout_lancement(
    client: TestClient, workspace: Path
) -> None:
    # Sans ça, l'IDE ne peut pas savoir si un projet est lançable : il affiche
    # le bouton partout, et l'apprend en échouant — le bouton disparaissait
    # alors sous le curseur, sans rien expliquer (ticket-146).
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])

    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert [s["nom"] for s in listing] == ["api"]
    assert listing[0]["en_cours"] is False
    assert listing[0]["pid"] is None


def test_un_projet_sans_declaration_liste_vide(client: TestClient) -> None:
    # C'est ce qui fait qu'aucun bouton ne s'affiche, dès le premier rendu.
    assert client.get("/api/v1/projects/sans-services/services").json() == []


def test_un_service_lance_garde_son_pid_dans_la_liste(
    client: TestClient, workspace: Path
) -> None:
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    _demarrer(client, "mon-projet")

    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert len(listing) == 1
    assert listing[0]["en_cours"] is True
    assert isinstance(listing[0]["pid"], int)
