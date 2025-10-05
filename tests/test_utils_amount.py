"""Unit tests for FundingScraper amount extraction helpers."""

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.utils import FundingScraper


class _DummyScraper(FundingScraper):
    def __init__(self) -> None:
        super().__init__("https://example.com", "dummy")


@pytest.fixture()
def scraper():
    instance = _DummyScraper()
    yield instance
    instance.session.close()


def test_extract_amount_supports_suffixes(scraper):
    result = scraper.extract_amount("Funding amount: £4k to £10k")
    assert result["min"] == 4000
    assert result["max"] == 10000


def test_extract_amount_handles_millions(scraper):
    result = scraper.extract_amount("You can apply for up to £1.5m")
    assert result["max"] == 1_500_000


def test_extract_amount_ignores_non_currency_numbers(scraper):
    result = scraper.extract_amount("Applications open in 2025 and close in 2026")
    assert result["max"] == 0


def test_extract_amount_discards_implausible_values(scraper):
    result = scraper.extract_amount("This programme has a £500 million overall budget")
    assert result["max"] == 0
