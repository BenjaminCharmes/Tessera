"""L'agent qui résout un conflit de rebase — ticket-090."""
from pathlib import Path

from vibe_ide.services.resolveur_conflit import ResolveurConflitService


class _FauxRunner:
    def __init__(self) -> None:
        self.appels: list[dict[str, object]] = []

    async def run(self, **kwargs: object) -> object:
        self.appels.append(kwargs)

        class _R:
            content = "résolu"

        return _R()


def test_le_service_ne_fait_rien_sans_fichier(tmp_path: Path) -> None:
    import asyncio

    runner = _FauxRunner()
    svc = ResolveurConflitService(runner, tmp_path)  # type: ignore[arg-type]

    asyncio.run(svc.resoudre(()))

    assert runner.appels == []


async def test_le_prompt_nomme_les_fichiers_et_leur_contenu(tmp_path: Path) -> None:
    # Sans le contenu marqué, l'agent devrait ouvrir les fichiers lui-même —
    # un tour de plus, et l'occasion de se tromper de fichier.
    (tmp_path / "app.py").write_text(
        "<<<<<<< HEAD\na = 1\n=======\na = 2\n>>>>>>> branche\n", encoding="utf-8"
    )
    runner = _FauxRunner()
    svc = ResolveurConflitService(runner, tmp_path)  # type: ignore[arg-type]

    await svc.resoudre(("app.py",))

    assert len(runner.appels) == 1
    prompt = str(runner.appels[0]["ticket"].body)  # type: ignore[union-attr]
    assert "app.py" in prompt
    assert "a = 1" in prompt and "a = 2" in prompt


async def test_un_fichier_disparu_ne_casse_pas_la_resolution(tmp_path: Path) -> None:
    runner = _FauxRunner()
    svc = ResolveurConflitService(runner, tmp_path)  # type: ignore[arg-type]

    await svc.resoudre(("jamais-vu.py",))

    assert len(runner.appels) == 1


async def test_l_agent_appele_est_le_resolveur(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x", encoding="utf-8")
    runner = _FauxRunner()
    svc = ResolveurConflitService(runner, tmp_path)  # type: ignore[arg-type]

    await svc.resoudre(("app.py",))

    assert runner.appels[0]["role"] == "resolveur-conflit"
