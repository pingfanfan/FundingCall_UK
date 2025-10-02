from datetime import datetime, timedelta, timezone

from scrapers.data_quality import sanitise_fundings


def _funding(template_id: str, deadline_offset: int, **overrides):
    now = datetime.now(timezone.utc)
    base = {
        "id": template_id,
        "title": f"Opportunity {template_id}",
        "organization": "Org",
        "category": "ukri",
        "subcategory": "sample",
        "description": "Description",
        "eligibility": {"career_stage": "Early Career"},
        "funding_details": {"amount": {"min": 1000, "max": 2000}},
        "application": {"deadline": (now + timedelta(days=deadline_offset)).date().isoformat()},
    }
    base.update(overrides)
    return base


def test_sanitise_filters_outside_window_and_duplicates():
    fundings = [
        _funding("valid", 10),
        _funding("duplicate", 15),
        _funding("duplicate", 15),
        _funding("old", -200),
        _funding("missing", 20, description=""),
        _funding("nodate", 0, application={}),
    ]

    curated, report = sanitise_fundings(fundings, window_months=3)

    assert len(curated) == 2
    ids = {item["id"] for item in curated}
    assert ids == {"valid", "duplicate"}
    assert report["dropped"]["duplicate"] == 1
    assert report["dropped"]["outside_window"] == 1
    assert report["dropped"]["missing_fields"] == 1
    assert report["dropped"]["undated"] == 1
