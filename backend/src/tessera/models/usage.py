"""Usage statistics payload — ticket-201."""
from pydantic import BaseModel


class UsageTotals(BaseModel):
    runs: int = 0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    pipeline_cost_usd: float = 0.0
    chat_cost_usd: float = 0.0
    #: Pipeline plus chat — ce que la période a coûté, tout compris.
    cost_usd: float = 0.0
    call_duration_ms: int = 0


class DailyPoint(BaseModel):
    """One UTC day. `cost_usd` includes the chat; runs and tokens do not."""

    day: str
    runs: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class BreakdownLine(BaseModel):
    """One agent, model or project, keyed by `key`."""

    key: str
    cost_usd: float
    tokens: int
    calls: int
    avg_duration_ms: float


class StatusCount(BaseModel):
    status: str
    count: int


class RunQuality(BaseModel):
    finished_runs: int = 0
    #: `None` sans run terminé : un taux sur zéro run n'est pas 0 %.
    approval_rate: float | None = None
    avg_rounds: float | None = None
    avg_run_duration_ms: float | None = None
    by_status: list[StatusCount] = []


class RecentRun(BaseModel):
    id: str
    project_id: str
    ticket_id: str
    started_at: str
    finished_at: str | None = None
    approved: bool | None = None
    final_status: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    #: `None` tant que le run n'est pas terminé.
    duration_ms: int | None = None


class UsageStats(BaseModel):
    days: int
    project_id: str | None
    #: Premier et dernier jour couverts, en UTC, bornes incluses.
    since: str
    until: str
    totals: UsageTotals
    daily: list[DailyPoint]
    per_agent: list[BreakdownLine]
    per_model: list[BreakdownLine]
    per_project: list[BreakdownLine]
    quality: RunQuality
    recent_runs: list[RecentRun]
