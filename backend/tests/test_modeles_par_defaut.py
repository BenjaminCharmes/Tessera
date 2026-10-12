"""Default models are current and defined once — ticket-397."""
import json
import re
from pathlib import Path

from tessera.services import security_auditor, validator
from tessera.services.modeles_par_defaut import (
    MODELE_JUGEMENT,
    MODELE_PRODUCTION,
    modele_par_defaut,
)
from tessera.services.project_loader import _default_agents_json

_SERVICES = Path(__file__).resolve().parents[1] / "src" / "tessera" / "services"
# Un identifiant daté (« claude-haiku-4-5-20251001 ») ou la génération retirée.
_PERIME = re.compile(r"claude-sonnet-4-6|claude-[a-z]+-\d+-\d+-\d{8}")


def test_no_stale_model_id_in_services() -> None:
    fautifs = [
        f"{p.name}: {m.group(0)}"
        for p in _SERVICES.rglob("*.py")
        if p.name != "cost_calculator.py"
        for m in _PERIME.finditer(p.read_text(encoding="utf-8"))
    ]
    assert fautifs == []


def test_default_manifest_uses_current_models() -> None:
    data = json.loads(
        _default_agents_json("p", ["codeur", "reviewer", "validateur"], "tracked")
    )
    modeles = {a["role"]: a["model"] for a in data["agents"]}
    assert modeles["codeur"] == MODELE_PRODUCTION
    assert modeles["reviewer"] == MODELE_PRODUCTION
    assert modeles["validateur"] == MODELE_JUGEMENT


def test_judgment_services_default_to_judgment_model() -> None:
    assert security_auditor._MODEL == MODELE_JUGEMENT
    assert validator._MODEL == MODELE_JUGEMENT
    assert modele_par_defaut("securite") == MODELE_JUGEMENT
    assert modele_par_defaut("architect") == MODELE_PRODUCTION
