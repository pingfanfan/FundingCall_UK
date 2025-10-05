"""Data quality helpers for filtering and validating scraped funding calls."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from utils import canonicalize_url, normalise_whitespace

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


def _select_deadline(
    funding: Dict,
    window_start: datetime,
    window_end: datetime,
) -> Tuple[datetime | None, str | None]:
    """Pick the most relevant deadline for a funding record."""

    application = funding.get("application") or {}

    # Honour any precomputed deadline first (for example from cached datasets).
    active_deadline = _to_datetime(application.get("active_deadline"))
    if active_deadline:
        return active_deadline, application.get("deadline_source")

    deadline = _to_datetime(application.get("deadline"))
    next_deadline = _to_datetime(application.get("next_deadline"))

    def _in_window(value: datetime | None) -> bool:
        return bool(value and window_start <= value <= window_end)

    if _in_window(deadline):
        return deadline, "deadline"

    if _in_window(next_deadline):
        return next_deadline, "next_deadline"

    # Prefer future dates even if slightly outside the strict window so that
    # recurring calls with stale ``deadline`` but fresh ``next_deadline`` survive
    # long enough to be revalidated on the next crawl.
    future_candidates = [
        (deadline, "deadline"),
        (next_deadline, "next_deadline"),
    ]
    for candidate, source in future_candidates:
        if candidate and candidate >= window_start:
            return candidate, source

    if deadline:
        return deadline, "deadline"

    if next_deadline:
        return next_deadline, "next_deadline"

    return None, None


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
    seen_sources: set[str] = set()
    seen_titles: set[str] = set()
    total_seen = 0
    dropped: Dict[str, int] = {
        "missing_fields": 0,
        "duplicate": 0,
        "undated": 0,
        "outside_window": 0,
    }
    duplicates: Dict[str, int] = {
        "id": 0,
        "source": 0,
        "title": 0,
    }
    substitutions: Dict[str, int] = {
        "primary_deadline_used": 0,
        "next_deadline_used": 0,
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

        # Normalise core string fields early so duplicate detection is reliable.
        funding["title"] = normalise_whitespace(funding.get("title", ""))
        funding["organization"] = normalise_whitespace(funding.get("organization", ""))
        funding["description"] = normalise_whitespace(funding.get("description", ""))

        identifier = str(funding["id"])
        if identifier in seen_ids:
            duplicates["id"] += 1
            dropped["duplicate"] += 1
            if log:
                log.warning(f"Discarded duplicate funding id {identifier}")
            continue
        seen_ids.add(identifier)

        source_url = canonicalize_url(
            funding.get("scraped_from")
            or (funding.get("application") or {}).get("application_url")
        )
        if source_url:
            parsed_source = urlparse(source_url)
            path = parsed_source.path or "/"
            # Treat bare domains as insufficient for duplicate detection; many
            # partner feeds only link to their homepage, so filtering on these
            # would collapse dozens of legitimate opportunities into one.
            if path not in {"", "/"}:
                if source_url in seen_sources:
                    duplicates["source"] += 1
                    dropped["duplicate"] += 1
                    if log:
                        log.warning(
                            "Discarded duplicate funding from source {source} (id {identifier})".format(
                                source=source_url,
                                identifier=identifier,
                            )
                        )
                    continue
                seen_sources.add(source_url)

        title_key = f"{funding['title'].lower()}::{funding['organization'].lower()}"
        if title_key in seen_titles:
            duplicates["title"] += 1
            dropped["duplicate"] += 1
            if log:
                log.warning(
                    "Discarded duplicate funding title '{title}' for organisation {org}".format(
                        title=funding["title"],
                        org=funding["organization"],
                    )
                )
            continue
        seen_titles.add(title_key)

        application = funding.setdefault("application", {})

        scraped_from = (funding.get("scraped_from") or "").strip()
        application_url = (application.get("application_url") or "").strip()
        if scraped_from and (not application_url or urlparse(application_url).path in {"", "/"}):
            application["application_url"] = scraped_from

        selected_deadline, source = _select_deadline(funding, window_start, window_end)

        if selected_deadline is None:
            dropped["undated"] += 1
            if log:
                log.warning(
                    f"Discarded funding {identifier} because the deadline is missing or invalid"
                )
            continue

        if not (window_start <= selected_deadline <= window_end):
            dropped["outside_window"] += 1
            if log:
                log.info(
                    "Filtered out funding {id} with deadline {deadline} outside of window {start} – {end}".format(
                        id=identifier,
                        deadline=selected_deadline.isoformat(),
                        start=window_start.isoformat(),
                        end=window_end.isoformat(),
                    )
                )
            continue

        if source == "next_deadline":
            substitutions["next_deadline_used"] += 1
        else:
            substitutions["primary_deadline_used"] += 1

        application["active_deadline"] = selected_deadline.isoformat()
        if source:
            application["deadline_source"] = source

        curated.append(funding)

    window_label = f"{window_start.strftime('%d %b %Y')} – {window_end.strftime('%d %b %Y')}"

    source_counter = Counter(funding.get("category", "uncategorised") for funding in curated)

    report: FundingQualityReport = FundingQualityReport(
        total=total_seen,
        retained=len(curated),
        dropped=dropped,
        window={
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "months": window_months,
            "label": window_label,
        },
        substitutions=substitutions,
        duplicates=duplicates,
        source_totals=dict(source_counter.most_common()),
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
