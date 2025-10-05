"""Utility module for generating AI-style summaries of funding data."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple


def _safe_get(dct: Dict, path: Iterable[str], default=""):
    current = dct
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def _format_currency(value: int) -> str:
    if value is None or value <= 0:
        return "Unknown"
    if value >= 1_000_000_000:
        return f"£{value/1_000_000_000:.2f}bn"
    if value >= 1_000_000:
        return f"£{value/1_000_000:.1f}m"
    if value >= 1_000:
        return f"£{value/1_000:.0f}k"
    return f"£{value:,}"


def _format_deadline(deadline: str) -> str:
    try:
        date_obj = datetime.fromisoformat(deadline)
    except (TypeError, ValueError):
        return "Date TBC"
    return date_obj.strftime("%d %b %Y")


def _extract_amount_range(funding: Dict) -> int:
    amount = funding.get("funding_details", {}).get("amount", {})
    return int(amount.get("max") or amount.get("min") or 0)


def _parse_deadline(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_active_deadline(funding: Dict) -> Tuple[Optional[datetime], Optional[str]]:
    application = funding.get("application") or {}
    for field in ("active_deadline", "deadline", "next_deadline"):
        candidate = _parse_deadline(application.get(field))
        if candidate:
            return candidate, field
    return None, None


def _resolve_window(window_days: int, quality_report: Optional[Dict]) -> Dict[str, str]:
    now = datetime.now(timezone.utc)
    default_start = now - timedelta(days=window_days)
    default_end = now + timedelta(days=window_days)

    if quality_report:
        window = quality_report.get("window", {})
        start = window.get("start")
        end = window.get("end")
        try:
            if start and end:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                return {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "label": f"{start_dt.strftime('%d %b %Y')} – {end_dt.strftime('%d %b %Y')}",
                }
        except ValueError:
            pass

    return {
        "start": default_start.isoformat(),
        "end": default_end.isoformat(),
        "label": f"{default_start.strftime('%d %b %Y')} – {default_end.strftime('%d %b %Y')}",
    }


def _quality_notes(quality_report: Optional[Dict]) -> List[str]:
    if not quality_report:
        return []

    dropped = quality_report.get("dropped", {})
    notes: List[str] = []
    drop_messages = {
        "missing_fields": "missing critical metadata",
        "duplicate": "duplicate identifiers",
        "undated": "undated deadlines",
        "outside_window": "deadlines outside the 3-month window",
    }

    for key, reason in drop_messages.items():
        count = dropped.get(key, 0)
        if count:
            notes.append(f"{count} entries skipped due to {reason}.")

    retained = quality_report.get("retained")
    total = quality_report.get("total")
    if retained is not None and total:
        notes.insert(0, f"Curated {retained} of {total} scraped opportunities after validation checks.")

    return notes


def generate_ai_summary(fundings: List[Dict], *, window_days: int = 90, quality_report: Optional[Dict] = None) -> Dict:
    """Create a structured natural-language summary for researchers."""
    generated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    total = len(fundings)
    window_info = _resolve_window(window_days, quality_report)
    notes = _quality_notes(quality_report)

    if total == 0:
        return {
            "generated_at": generated_at,
            "overall_summary": "No active funding opportunities were found in the latest crawl.",
            "highlights": [
                "The automated scrapers did not return any new opportunities today. Please check back later."
            ],
            "upcoming_deadlines": [],
            "top_funding_bodies": [],
            "career_stage_focus": [],
            "coverage_window": window_info,
            "quality_notes": notes,
        }

    category_counter = Counter(f.get("category", "Uncategorised") for f in fundings)
    top_categories = category_counter.most_common(3)

    organisations = Counter(f.get("organization", "Unknown organisation") for f in fundings)
    top_orgs = organisations.most_common(5)

    career_stage_counter = Counter(
        _safe_get(f, ("eligibility", "career_stage"), "All career stages") for f in fundings
    )
    top_career = career_stage_counter.most_common(3)

    # Upcoming deadlines within 14 days
    upcoming: List[Dict] = []
    now = datetime.now(timezone.utc)
    for funding in fundings:
        deadline_dt, source = _resolve_active_deadline(funding)
        if not deadline_dt:
            continue
        delta = (deadline_dt - now).days
        if 0 <= delta <= 14:
            upcoming.append({
                "title": funding.get("title", "Untitled opportunity"),
                "organization": funding.get("organization", ""),
                "deadline": deadline_dt.isoformat(),
                "days_remaining": delta,
                "deadline_source": source,
            })
    upcoming.sort(key=lambda item: item["days_remaining"])
    upcoming = upcoming[:5]

    # High value opportunities
    high_value_candidates = []
    for funding in fundings:
        deadline_dt, _ = _resolve_active_deadline(funding)
        high_value_candidates.append(
            {
                "title": funding.get("title", "Untitled opportunity"),
                "organization": funding.get("organization", ""),
                "amount": _extract_amount_range(funding),
                "deadline": deadline_dt.isoformat() if deadline_dt else None,
            }
        )

    high_value_candidates.sort(key=lambda item: item["amount"], reverse=True)

    high_value = []
    seen_titles = set()
    for item in high_value_candidates:
        key = (item["title"], item["organization"], item["amount"])
        if key in seen_titles:
            continue
        seen_titles.add(key)
        high_value.append(item)
        if len(high_value) == 5:
            break

    highlights = [
        f"Curated {total} funding opportunities with deadlines between {window_info['label']}."
    ]
    if top_categories:
        highlights.append(
            "Top thematic areas today: "
            + ", ".join(f"{name.upper()} ({count})" for name, count in top_categories)
            + "."
        )
    if upcoming:
        highlights.append(
            f"{len(upcoming)} opportunities are closing within the next two weeks; prioritise applications soon."
        )
    if high_value:
        highlights.append(
            f"Highest available award tops out at {_format_currency(high_value[0]['amount'])}."
        )

    retained = quality_report.get("retained") if quality_report else None
    total_seen = quality_report.get("total") if quality_report else None
    drop_count: Optional[int] = None
    if retained is not None and total_seen is not None:
        drop_count = max(total_seen - retained, 0)

    overall_bits = [
        f"Research funding hub refreshed: {total} active opportunities spanning {window_info['label']}.",
    ]
    if drop_count:
        overall_bits.append(f"Quality checks removed {drop_count} items before publishing.")
    if quality_report and quality_report.get("source_totals"):
        top_sources = list(quality_report["source_totals"].items())[:3]
        if top_sources:
            readable = ", ".join(f"{name.upper()}" for name, _ in top_sources)
            overall_bits.append(f"Coverage concentrates on {readable} programmes today.")

    overall_summary = " ".join(overall_bits)

    return {
        "generated_at": generated_at,
        "overall_summary": overall_summary,
        "highlights": highlights,
        "upcoming_deadlines": [
            {
                "title": item["title"],
                "organization": item["organization"],
                "deadline": _format_deadline(item["deadline"]),
                "days_remaining": item["days_remaining"],
            }
            for item in upcoming
        ],
        "top_funding_bodies": [
            {"organization": name, "opportunity_count": count}
            for name, count in top_orgs
        ],
        "career_stage_focus": [
            {"stage": name, "opportunity_count": count}
            for name, count in top_career
        ],
        "high_value_awards": [
            {
                "title": item["title"],
                "organization": item["organization"],
                "amount": _format_currency(item["amount"]),
                "deadline": _format_deadline(item["deadline"]),
            }
            for item in high_value
            if item["amount"] > 0
        ],
        "coverage_window": window_info,
        "quality_notes": notes,
    }
