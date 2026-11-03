"""A conflict settled by rule is journalled and never merged alone — ticket-548."""
from pathlib import Path

from tests.test_livraison import _FauxGit, _livrer, _service


class _GitAvecRegles(_FauxGit):
    """A rebase that settled files by rule and never called the resolver."""

    def __init__(self, regles: tuple[tuple[str, str], ...]) -> None:
        super().__init__()
        self.regles_appliquees = regles


async def test_a_rule_settled_conflict_is_named_in_the_delivery_steps(tmp_path: Path) -> None:
    git = _GitAvecRegles((("src/app.py", "imports"), ("README.md", "espacement")))
    svc, _git, _workflow = _service(tmp_path, "pr", git=git)

    livraison = await _livrer(svc)

    assert "conflit résolu par règle : src/app.py (imports)" in livraison.etapes
    assert "conflit résolu par règle : README.md (espacement)" in livraison.etapes
    assert len(livraison.etapes) == len(livraison.durees_ms)


async def test_a_rule_settled_conflict_opens_its_pr_and_is_not_merged_alone(
    tmp_path: Path,
) -> None:
    git = _GitAvecRegles((("src/app.py", "imports"),))
    svc, _git, workflow = _service(tmp_path, "merge", git=git)

    livraison = await _livrer(svc)

    assert livraison.pr_number == 7
    assert workflow.merges == []
    assert livraison.merged is False
    assert livraison.conflits == ("src/app.py",)
    assert "relire" in (livraison.arret or "").lower()


async def test_a_file_settled_by_two_rules_is_listed_once_among_the_conflicts(
    tmp_path: Path,
) -> None:
    git = _GitAvecRegles((("src/app.py", "imports"), ("src/app.py", "cote-unique")))
    svc, _git, _workflow = _service(tmp_path, "pr", git=git)

    livraison = await _livrer(svc)

    assert livraison.conflits == ("src/app.py",)


async def test_a_delivery_without_rule_keeps_merging_alone(tmp_path: Path) -> None:
    svc, _git, workflow = _service(tmp_path, "merge", git=_GitAvecRegles(()))

    livraison = await _livrer(svc)

    assert workflow.merges == [7]
    assert livraison.merged is True
    assert not any("par règle" in etape for etape in livraison.etapes)
