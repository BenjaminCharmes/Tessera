"""Request and answer bodies of the live-queue routes (tickets 478 and 513)."""
from pydantic import BaseModel, Field


class AppendRequest(BaseModel):
    ticket_ids: list[str] = Field(min_length=1)


class AppendResult(BaseModel):
    """What an append did: added at the end, left alone, or refused with a reason."""

    ajoutes: list[str]
    ignores: dict[str, str]
    refuses: dict[str, str]


class RemoveRequest(BaseModel):
    ticket_ids: list[str] = Field(min_length=1)


class RemoveResult(BaseModel):
    """What a removal did: taken out of the queue, absent, or refused with a reason."""

    retires: list[str]
    ignores: dict[str, str]
    refuses: dict[str, str]
