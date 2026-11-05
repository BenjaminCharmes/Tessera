"""Reading what pytest and vitest print: counts, summary line, failure blocks.

Séparé de `test_runner.py` (ticket-571) : ces fonctions ne lisent que du texte
et ne dépendent d'aucun type du lanceur.
"""
import re


def extract_counts(output: str) -> tuple[int, int]:
    """Return ``(total, failed)`` read from pytest or vitest output."""
    # pytest: "5 passed", "2 failed, 3 passed"
    m = re.search(r"(\d+) passed", output)
    passed_count = int(m.group(1)) if m else 0
    m_fail = re.search(r"(\d+) failed", output)
    failed_count = int(m_fail.group(1)) if m_fail else 0

    # jest/vitest: "Tests: 5 passed, 7 total"
    m_total = re.search(r"(\d+) total", output)
    total = int(m_total.group(1)) if m_total else (passed_count + failed_count)

    return total, failed_count


def extract_summary_line(output: str) -> str:
    """Extract the canonical summary line from pytest or vitest output.

    Prioritises the pytest timing banner (=== N failed, M passed in X.XXs ===)
    and the vitest summary line over the heuristic reverse scan, which can
    pick up warnings printed after the real summary (ticket-393).
    """
    # Priorité 1 : résumé final de pytest (=== N failed, M passed in X.XXs ===)
    for line in output.splitlines():
        stripped = line.strip()
        if (
            re.match(r"={4,}[^=]+={4,}$", stripped)
            and re.search(r"\d+.*in\s+[\d.]+s", stripped)
            and any(kw in stripped.lower() for kw in ("passed", "failed", "error"))
        ):
            return stripped[:200]

    # Priorité 2 : résumé de `pytest -q`, sans bandeaux (N failed, M passed in X.XXs)
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(
            r"\d+ (?:failed|passed|errors?)\b.*\bin\s+[\d.]+s\b", stripped
        ):
            return stripped[:200]

    # Priorité 3 : résumé vitest (Tests  N failed | M passed)
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"Tests\s+\d+", stripped, re.IGNORECASE) and any(
            kw in stripped.lower() for kw in ("passed", "failed")
        ):
            return stripped[:200]

    # Repli : heuristique (dernière ligne avec un mot-clé de test)
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line and any(
            kw in line.lower()
            for kw in ("passed", "failed", "error", "ok", "test")
        ):
            return line[:200]
    return ""


def extract_failure_details(output: str, max_chars: int = 8000) -> str:
    """Extract structured failure details from pytest or vitest output.

    Returns, in order: the 'short test summary info' section of pytest (or
    FAIL/× lines of vitest), then the FAILURES/ERRORS detail blocks.
    Truncated to ``max_chars`` characters, keeping the beginning.
    """
    short = extract_pytest_short_summary(output)
    failures = extract_pytest_failures_section(output)

    parts: list[str] = [p for p in (short, failures) if p]
    if not parts:
        vitest = extract_vitest_failures(output)
        if vitest:
            parts.append(vitest)

    combined = "\n\n".join(parts)
    return combined[:max_chars]


def extract_pytest_short_summary(output: str) -> str:
    """Extract FAILED/ERROR lines from the pytest 'short test summary info' section."""
    in_section = False
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"={4,}\s+short test summary info\s+={4,}", stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("="):
                break
            if stripped:
                result.append(stripped)

    return "\n".join(result)


def extract_pytest_failures_section(output: str) -> str:
    """Extract the FAILURES and ERRORS detail blocks from pytest output."""
    in_section = False
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        is_section_header = bool(re.match(r"={4,}[^=]+={4,}$", stripped))
        if is_section_header:
            if re.match(r"={4,}\s*(?:FAILURES|ERRORS)\s*={4,}$", stripped, re.IGNORECASE):
                in_section = True
                result.append(stripped)
            elif in_section:
                in_section = False
        elif in_section:
            result.append(line.rstrip())

    return "\n".join(result).strip()


def extract_vitest_failures(output: str) -> str:
    """Extract failing test names and assertion errors from vitest output."""
    result: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("×")
            or stripped.startswith("✗")
            or stripped.startswith("FAIL ")
            or stripped.startswith("AssertionError")
            or stripped.startswith("Error:")
        ):
            result.append(stripped)

    return "\n".join(result)


def extract_errors(output: str, max_errors: int = 5) -> list[str]:
    """Return the first lines that name a failure, at most ``max_errors``."""
    errors: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if any(kw in stripped.upper() for kw in ("FAILED", "ERROR", "ASSERT")):
            errors.append(stripped[:300])
        if len(errors) >= max_errors:
            break
    return errors
