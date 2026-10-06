"""Tests for ValidatorService (ticket-036)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from tessera.services.test_runner import EtapeTest, TestResult
from tessera.services.validator import (
    CriterionResult,
    ValidationResult,
    ValidatorService,
    extract_file_refs,
    _CITED_FILES_MAX_CHARS,
)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def service(provider: FakeProvider) -> ValidatorService:
    return ValidatorService(provider, Path("agents/prompts"))


def _set_response(provider: FakeProvider, data: dict) -> None:
    provider.set_content(json.dumps(data))


class TestValidatorService:
    async def test_approved_when_all_criteria_pass(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [{"criterion": "API returns 200", "passed": True, "note": ""}],
                "verdict": "APPROVED",
                "feedback": "All good.",
            },
        )

        result = await service.validate(
            criteria=["API returns 200"],
            code_produced="def get(): return 200",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert len(result.criteria) == 1
        assert result.criteria[0].passed is True

    async def test_changes_requested_when_criterion_fails(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": False,
                "criteria": [
                    {"criterion": "DB persisted", "passed": False, "note": "Only in memory"}
                ],
                "verdict": "CHANGES_REQUESTED",
                "feedback": "Session not persisted.",
            },
        )

        result = await service.validate(
            criteria=["DB persisted"],
            code_produced="session = {}",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert result.criteria[0].passed is False
        assert result.criteria[0].note == "Only in memory"

    async def test_auto_approved_when_no_criteria(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some code",
            test_result=None,
        )

        assert provider.calls == []
        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert result.criteria == []


class TestNoCriteriaCodeTickets:
    """A code ticket without acceptance criteria must not be auto-approved (ticket-360)."""

    async def test_feat_without_criteria_is_changes_requested(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some code",
            test_result=None,
            ticket_type="feat",
        )

        assert provider.calls == []
        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False

    async def test_fix_without_criteria_is_changes_requested(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some fix",
            test_result=None,
            ticket_type="fix",
        )

        assert provider.calls == []
        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False

    async def test_chore_without_criteria_is_still_approved(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some bookkeeping",
            test_result=None,
            ticket_type="chore",
        )

        assert provider.calls == []
        assert result.verdict == "APPROVED"

    async def test_code_ticket_without_criteria_message_names_section(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some code",
            test_result=None,
            ticket_type="feat",
        )

        assert "## Critères d'acceptation" in result.feedback

    async def test_includes_test_result_in_context(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [{"criterion": "tests pass", "passed": True, "note": ""}],
                "verdict": "APPROVED",
                "feedback": "OK",
            },
        )
        test_result = TestResult(
            passed=True, total=5, failed=0, output_summary="5 passed", errors=[], duration_ms=100
        )

        await service.validate(
            criteria=["tests pass"],
            code_produced="def foo(): pass",
            test_result=test_result,
        )

        assert len(provider.calls) == 1
        assert "5 passed" in provider.calls[0]["user"]

    async def test_lists_each_step_the_testeur_ran_with_its_exit_code(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # ticket-337 — « typecheck, lint et build passent » se refusait faute
        # de voir quelles commandes le testeur avait lancées.
        _set_response(provider, {"criteria": [], "feedback": "OK"})
        test_result = TestResult(
            passed=True, total=5, failed=0, output_summary="5 passed",
            etapes=[EtapeTest("npm run typecheck", 0), EtapeTest("npm run build", 0)],
        )

        await service.validate(
            criteria=["typecheck et build passent"],
            code_produced="code",
            test_result=test_result,
        )

        message = provider.calls[0]["user"]
        assert "`npm run typecheck` — exit 0" in message
        assert "`npm run build` — exit 0" in message

    async def test_changes_requested_on_invalid_json_response(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(provider, {})
        # empty dict — no verdict/all_passed keys
        result = await service.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )
        assert result.verdict == "CHANGES_REQUESTED"

    async def test_multiple_criteria_all_pass(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        criteria = ["Returns 200", "Writes to DB", "Sends email"]
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": c, "passed": True, "note": ""} for c in criteria
                ],
                "verdict": "APPROVED",
                "feedback": "All criteria satisfied.",
            },
        )

        result = await service.validate(
            criteria=criteria,
            code_produced="full implementation",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert len(result.criteria) == 3

    async def test_calls_provider_with_expected_shape(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [],
                "verdict": "APPROVED",
                "feedback": "ok",
            },
        )

        await service.validate(
            criteria=["Returns 200"],
            code_produced="def get(): return 200",
            test_result=None,
        )

        assert len(provider.calls) == 1
        call = provider.calls[0]
        assert call["mode"] == "complete"
        assert isinstance(call["system"], str)
        assert "Returns 200" in call["user"]
        assert "def get(): return 200" in call["user"]
        # Dix critères avec une `note` chacun tiennent mal dans 1 024 tokens :
        # le JSON était tronqué, donc « non parseable », donc CHANGES_REQUESTED
        # pour une raison qui n'avait rien à voir avec le code (ticket-126).
        assert call["max_tokens"] >= 2048

    async def test_changes_requested_quand_le_provider_est_indisponible(
        self, service: ValidatorService
    ) -> None:
        # Le validateur rendait CHANGES_REQUESTED sur un JSON illisible mais
        # APPROVED sur un provider en panne : deux pannes, deux verdicts
        # opposés. Une validation qui n'a pas eu lieu n'approuve rien
        # (ticket-122).
        class _FailingProvider(FakeProvider):
            async def complete(self, **kwargs):  # type: ignore[override]
                raise Exception("Network error")

        service_with_failure = ValidatorService(_FailingProvider(), Path("agents/prompts"))

        result = await service_with_failure.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert "Network error" in result.feedback


class TestCriteriaReconciliation:
    """Tests for criterion-level reconciliation (ticket-209)."""

    async def test_missing_criterion_causes_changes_requested(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # 3 critères envoyés, 2 jugés true dans la réponse → CHANGES_REQUESTED
        # et le troisième figure en passed: false
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Returns 200", "passed": True, "note": ""},
                    {"criterion": "Writes to DB", "passed": True, "note": ""},
                    # "Sends email" est absent de la réponse LLM
                ],
                "verdict": "APPROVED",
                "feedback": "Two criteria checked.",
            },
        )

        result = await service.validate(
            criteria=["Returns 200", "Writes to DB", "Sends email"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert len(result.criteria) == 3
        missing = next(c for c in result.criteria if "email" in c.criterion.lower())
        assert missing.passed is False
        assert "non jugé" in missing.note

    async def test_llm_approved_verdict_ignored_when_criterion_fails(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Le champ "verdict" du LLM dit APPROVED mais un critère est passed: false
        _set_response(
            provider,
            {
                "all_passed": False,
                "criteria": [
                    {"criterion": "PR merged", "passed": False, "note": "PR still open"},
                    {"criterion": "Tests pass", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "Mostly good.",
            },
        )

        result = await service.validate(
            criteria=["PR merged", "Tests pass"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False

    async def test_all_criteria_judged_true_gives_approved(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Non-régression : tous les critères jugés true → APPROVED
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Feature implemented", "passed": True, "note": ""},
                    {"criterion": "Tests written", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "All good.",
            },
        )

        result = await service.validate(
            criteria=["Feature implemented", "Tests written"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert all(c.passed for c in result.criteria)

    async def test_checkbox_prefix_normalized_for_matching(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Les critères du ticket arrivent avec "- [ ]" ; le LLM répond sans
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Tests pass", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "ok",
            },
        )

        result = await service.validate(
            criteria=["- [ ] Tests pass"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.criteria[0].passed is True


class TestValidationResult:
    def test_dataclass_fields(self) -> None:
        cr = CriterionResult(criterion="x", passed=True, note="")
        vr = ValidationResult(
            all_passed=True,
            criteria=[cr],
            verdict="APPROVED",
            feedback="ok",
        )
        assert vr.all_passed is True
        assert vr.verdict == "APPROVED"


class TestIndexAndTolerantMatching:
    """Tests for index-based and tolerant text matching (ticket-268)."""

    async def test_index_match_overrides_text_difference(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Un LLM qui rend index: 3 est rattaché au 3ème critère même si le
        # texte qu'il a recopié diffère du critère envoyé
        _set_response(
            provider,
            {
                "criteria": [
                    {"index": 1, "criterion": "First", "passed": True, "note": ""},
                    {"index": 2, "criterion": "Second", "passed": True, "note": ""},
                    {"index": 3, "criterion": "rewritten by llm", "passed": True, "note": ""},
                ],
                "feedback": "All good.",
            },
        )

        result = await service.validate(
            criteria=["First criterion", "Second criterion", "Third criterion original"],
            code_produced="code",
            test_result=None,
        )

        assert result.criteria[2].passed is True
        assert result.verdict == "APPROVED"

    async def test_tolerant_match_ignores_backticks_and_guillemets(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Le LLM répond sans backticks ni guillemets ; le critère envoyé en a.
        # La normalisation tolérante doit les rattacher l'un à l'autre.
        _set_response(
            provider,
            {
                "criteria": [
                    {
                        "criterion": "Un projet déclarant merge_method: squash fonctionne",
                        "passed": True,
                        "note": "",
                    },
                ],
                "feedback": "ok",
            },
        )

        result = await service.validate(
            criteria=['Un projet déclarant `"merge_method": "squash"` fonctionne'],
            code_produced="code",
            test_result=None,
        )

        assert result.criteria[0].passed is True
        assert result.verdict == "APPROVED"

    async def test_absent_criterion_stays_false_with_unjudged_note(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Un critère absent de la réponse reste passed: false avec la note attendue
        _set_response(
            provider,
            {
                "criteria": [
                    {"criterion": "First criterion", "passed": True, "note": ""},
                ],
                "feedback": "Only one judged.",
            },
        )

        result = await service.validate(
            criteria=["First criterion", "Second criterion absent from response"],
            code_produced="code",
            test_result=None,
        )

        assert result.criteria[1].passed is False
        assert "non jugé par le validateur" in result.criteria[1].note

    async def test_feedback_prefixed_when_criterion_not_judged(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Si un critère n'est pas jugé, le feedback commence par une phrase qui le signale
        _set_response(
            provider,
            {
                "criteria": [
                    {"criterion": "Judged criterion", "passed": True, "note": ""},
                ],
                "feedback": "One criterion checked.",
            },
        )

        result = await service.validate(
            criteria=["Judged criterion", "Unjudged criterion"],
            code_produced="code",
            test_result=None,
        )

        assert result.feedback.startswith("1 critère(s) absent(s)")


async def test_a_whole_branch_diff_reaches_the_validator_intact(
    service: ValidatorService, provider: FakeProvider
) -> None:
    # ticket-221 : coupé à 8 000 caractères, le validateur déclarait
    # invérifiables des critères que la fin du diff satisfaisait.
    _set_response(
        provider,
        {"criteria": [{"criterion": "Returns 200", "passed": True, "note": ""}]},
    )
    diff = "+x = 1\n" * 10_000 + "+SENTINELLE_FIN_DU_DIFF\n"

    await service.validate(criteria=["Returns 200"], code_produced=diff, test_result=None)

    assert "SENTINELLE_FIN_DU_DIFF" in provider.calls[0]["user"]


class TestCitedFiles:
    """Tests for the cited-files section injected into the validator message (ticket-316)."""

    def _approved_response(self) -> dict:
        return {
            "criteria": [{"index": 1, "criterion": "x", "passed": True, "note": ""}],
            "feedback": "ok",
        }

    async def test_criterion_citing_file_joins_its_content(
        self, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un critère qui cite `BillingTab.test.tsx:44` doit faire apparaître
        # le contenu du fichier dans le message envoyé au validateur.
        test_file = tmp_path / "BillingTab.test.tsx"
        test_file.write_text("describe('BillingTab', () => { it('shows empty state', () => {}) })")

        _set_response(provider, self._approved_response())
        svc = ValidatorService(provider, Path("agents/prompts"))

        await svc.validate(
            criteria=["Un test le vérifie dans `BillingTab.test.tsx:44`"],
            code_produced="some diff",
            test_result=None,
            project_root=tmp_path,
        )

        user_msg = provider.calls[0]["user"]
        assert "BillingTab.test.tsx" in user_msg
        assert "shows empty state" in user_msg

    async def test_absent_file_is_noted_without_exception(
        self, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un fichier cité mais absent du dépôt doit être signalé comme absent,
        # sans lever d'exception.
        _set_response(provider, self._approved_response())
        svc = ValidatorService(provider, Path("agents/prompts"))

        await svc.validate(
            criteria=["Le test est dans `AbsentFile.test.tsx`"],
            code_produced="some diff",
            test_result=None,
            project_root=tmp_path,
        )

        user_msg = provider.calls[0]["user"]
        assert "AbsentFile.test.tsx" in user_msg
        assert "absent" in user_msg.lower()

    async def test_section_truncated_when_file_exceeds_max_size(
        self, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Le contenu d'un fichier plus grand que le budget est tronqué,
        # avec une mention de troncature dans le message.
        oversized = "x" * (_CITED_FILES_MAX_CHARS + 5_000)
        (tmp_path / "BigFile.test.tsx").write_text(oversized)

        _set_response(provider, self._approved_response())
        svc = ValidatorService(provider, Path("agents/prompts"))

        await svc.validate(
            criteria=["check `BigFile.test.tsx`"],
            code_produced="code",
            test_result=None,
            project_root=tmp_path,
        )

        user_msg = provider.calls[0]["user"]
        # La section est présente mais le fichier n'y est pas en entier.
        assert "BigFile.test.tsx" in user_msg
        assert "tronqué" in user_msg
        # Le message ne contient pas les 25 000 « x » du fichier original.
        assert user_msg.count("x") < _CITED_FILES_MAX_CHARS + 5_000


# Frontière du projet pour les fichiers cités (audit sécurité, ticket-316)


def test_un_fichier_cite_hors_du_projet_n_est_pas_lu(tmp_path: Path) -> None:
    from tessera.services.validator import _find_file_in_project

    projet = tmp_path / "projet"
    projet.mkdir()
    (tmp_path / "secret.env").write_text("TOKEN=x", encoding="utf-8")

    assert _find_file_in_project("../secret.env", projet) is None


def test_un_chemin_absolu_cite_n_est_pas_lu(tmp_path: Path) -> None:
    from tessera.services.validator import _find_file_in_project

    projet = tmp_path / "projet"
    projet.mkdir()
    secret = tmp_path / "secret.env"
    secret.write_text("TOKEN=x", encoding="utf-8")

    assert _find_file_in_project(str(secret), projet) is None


def test_un_fichier_du_projet_reste_trouve(tmp_path: Path) -> None:
    from tessera.services.validator import _find_file_in_project

    projet = tmp_path / "projet"
    (projet / "src").mkdir(parents=True)
    cible = projet / "src" / "BillingTab.test.tsx"
    cible.write_text("test", encoding="utf-8")

    assert _find_file_in_project("src/BillingTab.test.tsx", projet) == cible
    assert _find_file_in_project("BillingTab.test.tsx", projet) == cible
