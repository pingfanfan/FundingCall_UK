import json
from pathlib import Path

from scrapers.summarizer import generate_ai_summary


def test_generate_ai_summary_structure():
    database_path = Path('data/funding_database.json')
    data = json.loads(database_path.read_text())
    fundings = data.get('fundings', [])

    summary = generate_ai_summary(fundings)

    assert 'overall_summary' in summary
    assert isinstance(summary['highlights'], list)
    assert isinstance(summary['top_funding_bodies'], list)
    assert isinstance(summary['career_stage_focus'], list)
    assert 'generated_at' in summary


def test_generate_ai_summary_empty():
    summary = generate_ai_summary([])
    assert summary['highlights'][0].startswith('The automated scrapers')
    assert summary['upcoming_deadlines'] == []
