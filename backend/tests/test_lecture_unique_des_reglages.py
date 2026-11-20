"""No module reads a changeable setting except through `reglages` (ticket-807)."""
import re
from pathlib import Path

from tessera.reglages import REGISTRE

SOURCES = Path(__file__).resolve().parent.parent / "src"
AUTORISES = {"reglages.py", "config.py"}


def _lectures_interdites(racine: Path) -> list[str]:
    motif = re.compile(r"\bsettings\.(" + "|".join(map(re.escape, REGISTRE)) + r")\b")
    trouvees: list[str] = []
    for fichier in sorted(racine.rglob("*.py")):
        if fichier.name in AUTORISES:
            continue
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            if motif.search(ligne):
                trouvees.append(f"{fichier.name}:{numero}: {ligne.strip()}")
    return trouvees


def test_no_module_reads_a_changeable_setting_from_settings() -> None:
    assert _lectures_interdites(SOURCES) == [], (
        "lis ces réglages par `tessera.reglages` (ADR-075)"
    )


def test_the_guard_catches_a_planted_read(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text(
        "x = settings.max_parallel_test_runs\n", encoding="utf-8"
    )
    assert len(_lectures_interdites(tmp_path)) == 1
