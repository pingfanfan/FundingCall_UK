"""Data quality helpers for filtering and validating scraped funding calls."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

REQUIRED_FIELDS: Tuple[str, ...] = (
    "id",
    "title",
    "organization",
    "category",
    "description",
)


class FundingQualityReport(Dict[str, object]):
    """Typed dictionary returned after sanitising funding calls."""


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def sanitise_fundings(
    fundings: Iterable[Dict],
    *,
    window_months: int = 3,
    log=None,
) -> Tuple[List[Dict], FundingQualityReport]:
    """Validate scraped fundings and enforce a rolling time window.

    Args:
        fundings: Raw funding payloads from scrapers.
        window_months: Symmetric window applied before/after now.
        log: Optional logger with ``info``/``warning`` methods.

    Returns:
        A tuple containing the curated list of fundings and a quality report
        describing dropped records.
    """

    now = datetime.now(timezone.utc)
    window_delta = timedelta(days=window_months * 30)
    window_start = now - window_delta
    window_end = now + window_delta

    curated: List[Dict] = []
    seen_ids: set[str] = set()
    total_seen = 0
    dropped: Dict[str, int] = {
        "missing_fields": 0,
        "duplicate": 0,
        "undated": 0,
        "outside_window": 0,
    }

    for funding in fundings:
        total_seen += 1
        missing = [field for field in REQUIRED_FIELDS if not funding.get(field)]
        if missing:
            dropped["missing_fields"] += 1
            if log:
                log.warning(
                    "Discarded funding {id} due to missing required fields: {fields}".format(
                        id=funding.get("id", "<unknown>"),
                        fields=", ".join(missing),
                    )
                )
            continue

        identifier = str(funding["id"])
        if identifier in seen_ids:
            dropped["duplicate"] += 1
            if log:
                log.warning(f"Discarded duplicate funding id {identifier}")
            continue
        seen_ids.add(identifier)

        deadline_str = (
            funding.get("application", {}) or {}
        ).get("deadline")
        deadline_dt = _to_datetime(deadline_str)
        if deadline_dt is None:
            dropped["undated"] += 1
            if log:
                log.warning(
                    f"Discarded funding {identifier} because the deadline is missing or invalid"
                )
            continue

        if not (window_start <= deadline_dt <= window_end):
            dropped["outside_window"] += 1
            if log:
                log.info(
                    "Filtered out funding {id} with deadline {deadline} outside of window {start} – {end}".format(
                        id=identifier,
                        deadline=deadline_dt.isoformat(),
                        start=window_start.isoformat(),
                        end=window_end.isoformat(),
                    )
                )
            continue

        curated.append(funding)

    report: FundingQualityReport = FundingQualityReport(
        total=total_seen,
        retained=len(curated),
        dropped=dropped,
        window={
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "months": window_months,
        },
    )

    if log:
        log.info(
            "Sanitised fundings: retained {retained} of {total} opportunities (window {start} to {end})".format(
                retained=report["retained"],
                total=report["total"],
                start=window_start.date(),
                end=window_end.date(),
            )
        )

    return curated, report
