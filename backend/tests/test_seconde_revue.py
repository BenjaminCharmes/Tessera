"""Tests for scripts/seconde_revue.py (ticket-844).

No model is called: a fake `LLMProvider` is injected through `construire`, and
the corpus diffs come from a temporary git repository.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from seconde_revue import BudgetAtteint, ResultatsIncompatibles, agents_json_temporaire, rejouer  # noqa: E402
from seconde_revue_corpus import Corpus, Entree, somme_gel  # noqa: E402
from seconde_revue_lecture import lire_resultats  # noqa: E402

from tessera.services.providers.base import ProviderResult  # noqa: E402
from tessera.services.providers.noms import ProviderIndisponible  # noqa: E402

_RACINE = _SCRIPTS_DIR.parent
_REFUS = {
    "verdict": "CHANGES_REQUESTED", "summary": "x",
    "blocking": [{"text": "défaut", "confidence": 95, "location": "a.txt:1"}],
}
_OK = {"verdict": "APPROVED", "summary": "x", "blocking": []}


class FauxProvider:
    """Records its calls and answers from a script."""

    name = "faux"

    def __init__(self, reponse: Any = None, cout: float | None = 0.0) -> None:
        self.reponse = _OK if reponse is None else reponse
        self.cout = cout
        self.appels: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> ProviderResult:
        self.appels.append(kwargs)
        if isinstance(self.reponse, Exception):
            raise self.reponse
        structured = self.reponse
        return ProviderResult(content="{}", cost_usd=self.cout, structured=structured)


def _git(depot: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(depot), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture
def monde(tmp_path: Path) -> dict[str, Any]:
    """A repository with three squash-like commits, the tickets and a corpus."""
    depot = tmp_path / "depot"
    depot.mkdir()
    _git(depot, "init", "-q")
    shas: list[str] = []
    for i in range(4):
        (depot / "a.txt").write_text("\n".join(f"ligne {n}" for n in range(i + 1)) + "\n")
        _git(depot, "add", "a.txt")
        _git(depot, "commit", "-q", "-m", f"c{i}")
        shas.append(_git(depot, "rev-parse", "HEAD"))
    tickets = tmp_path / "tickets"
    (tickets / "done").mkdir(parents=True)
    entrees = []
    for i, sha in enumerate(shas[1:]):
        (tickets / "done" / f"ticket-90{i}-sujet.md").write_text(f"corps {i}", encoding="utf-8")
        defaut = i == 0
        entrees.append(Entree(
            id=f"e{i}", ticket=f"ticket-90{i}", sha=sha, classe="defaut" if defaut else "sain",
            preuve="fix" if defaut else "", fichiers_defaut=("a.txt",) if defaut else (),
            defaut="d" if defaut else "", sensible=False,
        ))
    corpus = Corpus(entrees=tuple(entrees), gel_sha256=somme_gel(entrees))
    return {"depot": depot, "tickets": tickets, "corpus": corpus, "sortie": tmp_path / "r.jsonl"}


def _lancer(monde: dict[str, Any], provider: FauxProvider, bras: str = "C", *,
            budget: float = 10.0, fenetre: int | None = None,
            suivis: list[Path] | None = None, corpus: Corpus | None = None) -> list[Any]:
    def construire(dossier: Path, role: str) -> FauxProvider:
        if suivis is not None:
            suivis.append(dossier)
        return provider

    return asyncio.run(rejouer(
        corpus or monde["corpus"], bras, "ollama", "modele-x",
        depot=monde["depot"], racine_tickets=monde["tickets"], sortie=monde["sortie"],
        budget_usd=budget,
        fenetre_caracteres=10**9 if fenetre is None else fenetre, construire=construire,  # type: ignore[arg-type]
    ))


def test_rejouer_records_an_ok_line_with_cost_and_duration(monde: dict[str, Any]) -> None:
    faux = FauxProvider(_REFUS, cout=0.25)
    _lancer(monde, faux)
    lignes = lire_resultats(monde["sortie"])
    assert [r.id for r in lignes] == ["e0", "e1", "e2"]
    premiere = lignes[0]
    assert premiere.etat == "ok" and premiere.leve is True and premiere.bras == "C"
    assert premiere.cout_usd == 0.25 and premiere.duree_ms >= 0
    assert premiere.gel_sha256 == monde["corpus"].gel_sha256
    assert premiere.remarques[0]["text"] == "défaut"
    appel = faux.appels[0]
    assert "corps 0" in appel["user"] and "## Code produit par le codeur" in appel["user"]
    assert appel["schema"]["required"] == ["verdict", "summary", "blocking"]
    assert appel["model"] == "modele-x"


def test_rejouer_sends_nothing_beyond_the_window(monde: dict[str, Any]) -> None:
    faux = FauxProvider()
    _lancer(monde, faux, fenetre=10)
    assert faux.appels == []
    assert {r.etat for r in lire_resultats(monde["sortie"])} == {"hors_fenetre"}


def test_rejouer_an_unavailable_provider_is_recorded_without_a_second_call(
    monde: dict[str, Any],
) -> None:
    faux = FauxProvider(ProviderIndisponible("hors ligne"))
    _lancer(monde, faux)
    assert len(faux.appels) == len(monde["corpus"].entrees)
    assert {r.etat for r in lire_resultats(monde["sortie"])} == {"indisponible"}
    assert all(r.leve is None for r in lire_resultats(monde["sortie"]))


def test_rejouer_an_unavailable_provider_is_not_retried_on_the_same_entry(
    monde: dict[str, Any],
) -> None:
    faux = FauxProvider(ProviderIndisponible("hors ligne"))
    un = Corpus(entrees=monde["corpus"].entrees[:1], gel_sha256=monde["corpus"].gel_sha256)
    _lancer(monde, faux, corpus=replace(un, gel_sha256=somme_gel(un.entrees)))
    assert len(faux.appels) == 1


def test_rejouer_an_absent_or_off_schema_output_is_hors_schema(monde: dict[str, Any]) -> None:
    for sortie in (None, {"verdict": "PEUT-ETRE"}):
        monde["sortie"].unlink(missing_ok=True)
        faux = FauxProvider(reponse=sortie)
        faux.reponse = sortie
        _lancer(monde, faux)
        lignes = lire_resultats(monde["sortie"])
        assert {r.etat for r in lignes} == {"hors_schema"} and len(lignes) == 3


def test_rejouer_stops_before_the_call_that_would_pass_the_cap(monde: dict[str, Any]) -> None:
    faux = FauxProvider(_OK, cout=0.6)
    with pytest.raises(BudgetAtteint) as erreur:
        _lancer(monde, faux, budget=1.0)
    assert len(faux.appels) == 1
    assert erreur.value.restantes == 2
    assert [r.id for r in lire_resultats(monde["sortie"])] == ["e0"]


def test_rejouer_resumes_without_replaying_a_finished_entry(monde: dict[str, Any]) -> None:
    premier = FauxProvider()
    _lancer(monde, premier)
    second = FauxProvider()
    _lancer(monde, second)
    assert second.appels == []
    assert len(lire_resultats(monde["sortie"])) == 3
    # Un autre bras garde son propre état d'avancement.
    autre = FauxProvider()
    _lancer(monde, autre, bras="B")
    assert len(autre.appels) == 3


def test_rejouer_refuses_a_results_file_of_another_freeze(monde: dict[str, Any]) -> None:
    _lancer(monde, FauxProvider())
    ligne = json.loads(monde["sortie"].read_text(encoding="utf-8").splitlines()[0])
    ligne["gel_sha256"] = "autre"
    monde["sortie"].write_text(json.dumps(ligne) + "\n", encoding="utf-8")
    faux = FauxProvider()
    with pytest.raises(ResultatsIncompatibles):
        _lancer(monde, faux)
    assert faux.appels == []


def test_agents_json_temporaire_declares_one_role_and_no_fallback(tmp_path: Path) -> None:
    projet = agents_json_temporaire(tmp_path, "C", "ollama", "modele-x")
    contenu = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    assert len(contenu["agents"]) == 1
    role = contenu["agents"][0]
    assert role["role"] == "candidat" and role["provider"] == "ollama"
    assert role["model"] == "modele-x" and "fallback" not in role
    projet_b = agents_json_temporaire(tmp_path / "b", "B", "agent_sdk", "m")
    assert json.loads((projet_b / "agents.json").read_text())["agents"][0]["role"] == "reviewer"


def test_temporary_folder_is_removed_even_on_error_and_the_manifest_is_untouched(
    monde: dict[str, Any],
) -> None:
    manifeste = _RACINE / "projects" / "ide-core" / "agents.json"
    avant = manifeste.read_bytes()
    suivis: list[Path] = []
    _lancer(monde, FauxProvider(), suivis=suivis)
    assert suivis and not suivis[0].exists()
    suivis.clear()
    monde["sortie"].unlink()
    with pytest.raises(RuntimeError, match="boum"):
        _lancer(monde, FauxProvider(RuntimeError("boum")), suivis=suivis)
    assert suivis and not suivis[0].exists()
    assert manifeste.read_bytes() == avant


def test_script_never_names_the_global_provider_factory_nor_the_product_the_script() -> None:
    assert "get_provider" not in (_SCRIPTS_DIR / "seconde_revue.py").read_text(encoding="utf-8")
    for fichier in (_RACINE / "backend" / "src").rglob("*.py"):
        assert "seconde_revue" not in fichier.read_text(encoding="utf-8")


def test_rejouer_refuses_an_ollama_candidate_without_a_window(monde: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="fenêtre"):
        asyncio.run(rejouer(
            monde["corpus"], "C", "ollama", "m", depot=monde["depot"],
            racine_tickets=monde["tickets"], sortie=monde["sortie"],
            budget_usd=1.0, fenetre_caracteres=None,
        ))
