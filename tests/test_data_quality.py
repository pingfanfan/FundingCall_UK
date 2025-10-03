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
    assert report["substitutions"]["primary_deadline_used"] == 2
    assert report["duplicates"]["id"] == 1


def test_sanitise_uses_next_deadline_when_primary_is_stale():
    now = datetime.now(timezone.utc)
    stale = _funding("stale", -200)
    stale["application"]["next_deadline"] = (now + timedelta(days=45)).date().isoformat()

    curated, report = sanitise_fundings([stale], window_months=3)

    assert len(curated) == 1
    active_deadline = curated[0]["application"]["active_deadline"]
    assert active_deadline is not None
    assert report["substitutions"]["next_deadline_used"] == 1


def test_duplicate_detection_uses_urls_and_titles():
    now = datetime.now(timezone.utc)
    base_deadline = (now + timedelta(days=10)).date().isoformat()

    template = {
        "title": "Shared Call",
        "organization": "Org",
        "category": "ukri",
        "subcategory": "sample",
        "description": "Description",
        "eligibility": {"career_stage": "Early Career"},
        "funding_details": {"amount": {"min": 1, "max": 2}},
        "application": {"deadline": base_deadline, "application_url": "https://example.com/opportunity"},
        "scraped_from": "https://example.com/opportunity?utm_source=newsletter",
    }

    fundings = [
        {"id": "first", **template},
        {"id": "second", **template},  # duplicate by URL after canonicalisation
        {
            "id": "third",
            **{**template, "title": "Shared  Call", "scraped_from": "https://example.com/other"},
        },  # duplicate by normalised title/org
    ]

    curated, report = sanitise_fundings(fundings, window_months=3)

    assert len(curated) == 1
    assert report["duplicates"]["source"] == 1
    assert report["duplicates"]["title"] == 1
    assert report["dropped"]["duplicate"] == 2
