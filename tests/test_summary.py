from datetime import datetime, timedelta, timezone

from scrapers.data_quality import sanitise_fundings
from scrapers.summarizer import generate_ai_summary


def _sample_fundings():
    now = datetime.now(timezone.utc)
    base_deadline = (now + timedelta(days=10)).date().isoformat()
    return [
        {
            "id": "sample-1",
            "title": "Sample Opportunity",
            "organization": "Sample Council",
            "category": "ukri",
            "subcategory": "sample",
            "description": "Support for innovative sample projects.",
            "eligibility": {"career_stage": "Early Career", "requirements": []},
            "funding_details": {"amount": {"min": 100000, "max": 250000, "currency": "GBP"}},
            "application": {"deadline": base_deadline, "application_url": "https://example.com"},
            "key_info": {"competition_level": "Competitive"},
        },
        {
            "id": "sample-2",
            "title": "Flagship Fellowship",
            "organization": "National Academy",
            "category": "academies",
            "subcategory": "academy",
            "description": "Fellowship funding for interdisciplinary work.",
            "eligibility": {"career_stage": "Mid Career", "requirements": []},
            "funding_details": {"amount": {"min": 50000, "max": 150000, "currency": "GBP"}},
            "application": {"deadline": (now + timedelta(days=50)).date().isoformat()},
            "key_info": {"competition_level": "Moderate"},
        },
    ]


def test_generate_ai_summary_structure():
    fundings = _sample_fundings()
    curated, report = sanitise_fundings(fundings, window_months=3)

    summary = generate_ai_summary(curated, quality_report=report)

    assert summary["overall_summary"].startswith("Research funding hub refreshed")
    assert isinstance(summary["highlights"], list) and summary["highlights"]
    assert isinstance(summary["quality_notes"], list)
    assert "coverage_window" in summary and "label" in summary["coverage_window"]
    assert summary["top_funding_bodies"][0]["organization"] == "Sample Council"
    if summary["upcoming_deadlines"]:
        assert summary["upcoming_deadlines"][0].get("deadline_source") in {None, "deadline", "active_deadline", "next_deadline"}


def test_generate_ai_summary_empty():
    summary = generate_ai_summary([])
    assert summary["highlights"][0].startswith("The automated scrapers")
    assert summary["upcoming_deadlines"] == []
    assert summary["quality_notes"] == []
