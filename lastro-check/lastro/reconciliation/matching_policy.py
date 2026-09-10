from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"


class MatchMethod(str, Enum):
    EXACT_REFERENCE = "EXACT_REFERENCE"
    BOUNDED_HEURISTIC = "BOUNDED_HEURISTIC"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class MatchEvent:
    event_id: str
    event_date: date
    reference: str | None = None
    reference_is_strong: bool = False


@dataclass(frozen=True, slots=True)
class MatchPolicy:
    allow_heuristic: bool = False
    max_date_delta_days: int | None = None

    def __post_init__(self) -> None:
        if self.max_date_delta_days is not None:
            if not isinstance(self.max_date_delta_days, int) or isinstance(self.max_date_delta_days, bool) or self.max_date_delta_days < 0:
                raise ValueError("max_date_delta_days must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class CandidateAudit:
    event_id: str
    date_delta_days: int
    exact_reference: bool
    inside_date_window: bool


@dataclass(frozen=True, slots=True)
class MatchDecision:
    status: MatchStatus
    method: MatchMethod
    matched_event_id: str | None
    candidates: tuple[CandidateAudit, ...]
    reason: str


def _audit_candidates(target: MatchEvent, candidates: Iterable[MatchEvent], policy: MatchPolicy) -> tuple[CandidateAudit, ...]:
    audited = []
    for candidate in candidates:
        if candidate.event_id == target.event_id:
            continue
        delta = abs((candidate.event_date - target.event_date).days)
        exact = bool(target.reference and candidate.reference and target.reference_is_strong and candidate.reference_is_strong and candidate.reference == target.reference)
        inside = bool(policy.max_date_delta_days is not None and delta <= policy.max_date_delta_days)
        audited.append(CandidateAudit(candidate.event_id, delta, exact, inside))
    return tuple(sorted(audited, key=lambda item: (item.date_delta_days, item.event_id)))


def decide_match(target: MatchEvent, candidates: Iterable[MatchEvent], policy: MatchPolicy) -> MatchDecision:
    audited = _audit_candidates(target, candidates, policy)
    exact = tuple(item for item in audited if item.exact_reference and (policy.max_date_delta_days is None or item.inside_date_window))
    if len(exact) == 1:
        return MatchDecision(MatchStatus.MATCHED, MatchMethod.EXACT_REFERENCE, exact[0].event_id, audited, "one strong exact reference matched")
    if len(exact) > 1:
        return MatchDecision(MatchStatus.AMBIGUOUS, MatchMethod.EXACT_REFERENCE, None, audited, "duplicate exact reference candidates")
    if not policy.allow_heuristic or policy.max_date_delta_days is None:
        return MatchDecision(MatchStatus.UNMATCHED, MatchMethod.NONE, None, audited, "heuristic matching unavailable")
    bounded = tuple(item for item in audited if item.inside_date_window)
    if len(bounded) == 1:
        return MatchDecision(MatchStatus.MATCHED, MatchMethod.BOUNDED_HEURISTIC, bounded[0].event_id, audited, "one candidate inside date window")
    if len(bounded) > 1:
        return MatchDecision(MatchStatus.AMBIGUOUS, MatchMethod.BOUNDED_HEURISTIC, None, audited, "multiple candidates inside date window")
    return MatchDecision(MatchStatus.UNMATCHED, MatchMethod.NONE, None, audited, "no supported candidate")
