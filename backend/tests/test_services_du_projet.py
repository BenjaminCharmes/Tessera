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
import os
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
    # (ticket-146). Il garde son pid depuis ticket-151 : l'effacer faisait
    # afficher « pas lancé par l'IDE » pour un service qu'on venait d'arrêter.
    assert [s["nom"] for s in listing] == ["api"]
    assert listing[0]["en_cours"] is False
    assert listing[0]["pid"] is not None


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

    # Arrêté à la main : ni « en cours », ni en échec. `terminate()` laisse
    # pourtant un code non nul, donc c'est un drapeau explicite qui porte
    # l'information — pas une déduction sur le code (ticket-151).
    assert listing[0]["en_cours"] is False
    assert listing[0]["arrete_a_la_main"] is True


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


# --------------------------------------------------------------------------
# La sortie survit à qui n'écoutait pas — ticket-148
# --------------------------------------------------------------------------


def test_la_sortie_est_conservee_pour_qui_arrive_apres(
    client: TestClient, workspace: Path
) -> None:
    # Le hub ne rejoue pas l'historique : un service écrit son adresse dans
    # ses deux premières secondes, et qui n'écoutait pas ne la voit jamais.
    # Le panneau affichait « n'a encore rien écrit » pour un service qui
    # tournait depuis dix minutes (ticket-148).
    import time

    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _BAVARD}])
    _demarrer(client, "mon-projet")

    for _ in range(40):
        listing = client.get("/api/v1/projects/mon-projet/services").json()
        if listing and listing[0].get("sortie"):
            break
        time.sleep(0.1)

    assert listing[0]["sortie"], listing
    assert any("je suis la" in ligne for ligne in listing[0]["sortie"])


def test_la_sortie_conservee_est_bornee(workspace: Path) -> None:
    # Garder les lignes fait grossir le registre : la borne est ce qui
    # l'empêche, et elle garde les plus récentes.
    from tessera.services.process_registry import LIGNES_CONSERVEES, Service

    service = Service(nom="api", project_id="mon-projet")
    for i in range(LIGNES_CONSERVEES + 50):
        service.noter(f"ligne {i}")

    assert len(service.sortie) == LIGNES_CONSERVEES
    assert service.sortie[-1] == f"ligne {LIGNES_CONSERVEES + 49}"


def test_les_couleurs_ansi_sont_retirees_de_la_sortie() -> None:
    # Vite colore sa sortie, et les codes tombent **au milieu** de l'URL :
    #   http://localhost:\x1b[1m5175\x1b[22m/\x1b[39m
    # L'adresse était donc extraite corrompue, et le `<pre>` du panneau
    # affichait « [32m » un peu partout (ticket-148).
    from tessera.services.process_registry import sans_couleurs

    brut = "  \x1b[32m➜\x1b[39m  \x1b[1mLocal\x1b[22m:   \x1b[36mhttp://localhost:\x1b[1m5175\x1b[22m/\x1b[39m"

    propre = sans_couleurs(brut)

    assert "\x1b" not in propre
    assert "http://localhost:5175/" in propre


def test_une_ligne_sans_couleur_n_est_pas_modifiee() -> None:
    from tessera.services.process_registry import sans_couleurs

    assert sans_couleurs("INFO: Uvicorn running on http://127.0.0.1:8000") == (
        "INFO: Uvicorn running on http://127.0.0.1:8000"
    )


# --------------------------------------------------------------------------
# Arrêter ne doit pas effacer la trace — ticket-151
# --------------------------------------------------------------------------


def test_un_service_arrete_garde_son_pid_et_sa_sortie(
    client: TestClient, workspace: Path
) -> None:
    # `arreter()` faisait `pop()` : toute trace disparaissait, et le service
    # déclaré se reconstruisait sans pid — d'où « pas lancé par l'IDE » pour
    # un service qu'on venait d'arrêter soi-même (ticket-151).
    import time

    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _BAVARD}])
    _demarrer(client, "mon-projet")
    for _ in range(40):
        listing = client.get("/api/v1/projects/mon-projet/services").json()
        if listing and listing[0].get("sortie"):
            break
        time.sleep(0.1)

    client.post("/api/v1/projects/mon-projet/services/stop")
    apres = client.get("/api/v1/projects/mon-projet/services").json()

    assert [s["nom"] for s in apres] == ["api"]
    assert apres[0]["en_cours"] is False
    assert apres[0]["pid"] is not None, "le pid a disparu : trace effacée"
    assert apres[0]["sortie"], "la sortie a disparu avec l'arrêt"


def test_un_start_apres_un_stop_ne_laisse_qu_une_entree(
    client: TestClient, workspace: Path
) -> None:
    # Garder la trace ne doit pas faire grossir la liste à chaque cycle.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    _demarrer(client, "mon-projet")
    client.post("/api/v1/projects/mon-projet/services/stop")
    _demarrer(client, "mon-projet")

    listing = client.get("/api/v1/projects/mon-projet/services").json()

    assert len([s for s in listing if s["nom"] == "api"]) == 1
    assert listing[0]["en_cours"] is True


# --------------------------------------------------------------------------
# L'arbre de processus, et le double lancement — ticket-153
# --------------------------------------------------------------------------

#: Un service qui engendre un enfant, comme `npm run dev` lance `concurrently`
#: qui lance deux serveurs. C'est le petit-enfant qui survivait à l'arrêt.
_AVEC_ENFANT = (
    f'"{sys.executable}" -c '
    '"import subprocess,sys,time; '
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']); "
    'time.sleep(120)"'
)


def test_arreter_ne_laisse_aucun_descendant(
    client: TestClient, workspace: Path
) -> None:
    # `stop` répondait « 2 arrêtés » pendant que douze processus tournaient
    # encore : `terminate()` frappe le premier maillon, et `concurrently` et
    # ses serveurs survivaient avec leurs ports (ticket-153).
    import time

    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _AVEC_ENFANT}])
    _demarrer(client, "mon-projet")
    time.sleep(2)
    parent = PROCESS_REGISTRY.services_de("mon-projet")[0].pid
    assert parent is not None
    enfants = _descendants(parent)
    assert enfants, "le service n'a pas engendré d'enfant : test sans objet"

    client.post("/api/v1/projects/mon-projet/services/stop")
    time.sleep(2)

    survivants = [pid for pid in enfants if _pid_vivant(pid)]
    assert survivants == [], f"descendants survivants : {survivants}"


def test_relancer_un_service_en_cours_est_refuse(
    client: TestClient, workspace: Path
) -> None:
    # Deux lancements de suite laissaient douze processus là où trois
    # suffisent, et la liste n'en montrait qu'un : elle indexait par nom.
    _manifeste(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    premier = _demarrer(client, "mon-projet")

    refus = client.post("/api/v1/projects/mon-projet/services/start")

    assert refus.status_code == 409
    assert "api" in refus.json()["detail"]
    listing = client.get("/api/v1/projects/mon-projet/services").json()
    assert len(listing) == 1
    assert listing[0]["pid"] == premier["services"][0]["pid"]


def _pid_vivant(pid: int) -> bool:
    import subprocess as sp

    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    sortie = sp.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True
    ).stdout
    return str(pid) in sortie


def _descendants(pid: int) -> list[int]:
    import subprocess as sp

    if os.name != "nt":
        # `ps --ppid` et non un simple `[]` : rendre la liste vide faisait
        # passer le test pour un succès alors qu'il n'observait rien. Sous
        # Linux l'arbre se tue par `killpg`, donc le cas est réel ici aussi.
        sortie = sp.run(
            ["ps", "-o", "pid=", "--ppid", str(pid)],
            capture_output=True,
            text=True,
        ).stdout
        return [int(l) for l in sortie.split() if l.strip().isdigit()]
    sortie = sp.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-CimInstance Win32_Process -Filter \"ParentProcessId={pid}\" | "
            "Select-Object -ExpandProperty ProcessId",
        ],
        capture_output=True,
        text=True,
    ).stdout
    return [int(l) for l in sortie.split() if l.strip().isdigit()]
