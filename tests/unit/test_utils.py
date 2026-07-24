# tests/unit/test_utils.py
"""Tests for form-parsing utilities."""

import pytest

from domain.models import PageRange
from utils import allowed_file, parse_page_range_from_form


class TestAllowedFile:
    """Test upload extension filtering."""

    @pytest.mark.parametrize("filename", ["paper.pdf", "PAPER.PDF", "a.b.pdf"])
    def test_accepts_pdf(self, filename: str):
        """Should accept .pdf in any case."""
        assert allowed_file(filename) is True

    @pytest.mark.parametrize("filename", ["paper.txt", "paper", "pdf", ".pdf.exe"])
    def test_rejects_non_pdf(self, filename: str):
        """Should reject anything that is not a .pdf."""
        assert allowed_file(filename) is False


class TestParsePageRangeFromForm:
    """Test page range parsing and validation."""

    def test_unchecked_box_returns_full_document(self):
        """Fields are ignored when use_page_range is off."""
        form = {"start_page": "garbage", "end_page": "-3"}
        assert parse_page_range_from_form(form) == PageRange()

    def test_parses_valid_range(self):
        """Should parse both bounds as integers."""
        form = {"use_page_range": "on", "start_page": "2", "end_page": "5"}
        assert parse_page_range_from_form(form) == PageRange(start_page=2, end_page=5)

    def test_parses_open_ended_range(self):
        """A missing bound stays None."""
        form = {"use_page_range": "on", "start_page": "3", "end_page": ""}
        assert parse_page_range_from_form(form) == PageRange(start_page=3, end_page=None)

    @pytest.mark.parametrize("bad_value", ["abc", "1.5", "2; DROP TABLE", " "])
    def test_rejects_non_numeric_input(self, bad_value: str):
        """Garbage input should raise a clear ValueError, not a bare int() crash."""
        form = {"use_page_range": "on", "start_page": bad_value.strip() or "abc", "end_page": "5"}
        with pytest.raises(ValueError, match="whole number"):
            parse_page_range_from_form(form)

    @pytest.mark.parametrize("bad_value", ["0", "-1", "-99"])
    def test_rejects_non_positive_pages(self, bad_value: str):
        """Pages are 1-based; zero and negatives are invalid."""
        form = {"use_page_range": "on", "start_page": bad_value, "end_page": ""}
        with pytest.raises(ValueError, match="1 or greater"):
            parse_page_range_from_form(form)

    def test_rejects_inverted_range(self):
        """A start page after the end page would silently extract nothing downstream."""
        form = {"use_page_range": "on", "start_page": "7", "end_page": "3"}
        with pytest.raises(ValueError, match="cannot be after"):
            parse_page_range_from_form(form)
