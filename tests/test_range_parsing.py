"""Unit tests for range parsing in Austrian real estate extractor."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from utils.extractors import AustrianRealEstateExtractor


class TestRangeParsing:
    """Test range detection and parsing."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing."""
        return AustrianRealEstateExtractor()

    def test_range_parsing_basic_dash(self, extractor):
        """Test basic dash-separated ranges."""
        assert extractor.parse_number_with_range("40-140") == 40.0
        assert extractor.parse_number_with_range("40 - 140") == 40.0
        assert extractor.parse_number_with_range("100-200") == 100.0

    def test_range_parsing_bis(self, extractor):
        """Test German 'bis' separator."""
        assert extractor.parse_number_with_range("40 bis 140") == 40.0
        assert extractor.parse_number_with_range("100 BIS 200") == 100.0

    def test_range_parsing_tilde(self, extractor):
        """Test tilde separator."""
        assert extractor.parse_number_with_range("40~140") == 40.0
        assert extractor.parse_number_with_range("40 ~ 140") == 40.0

    def test_range_parsing_to(self, extractor):
        """Test 'to' separator."""
        assert extractor.parse_number_with_range("40 to 140") == 40.0
        assert extractor.parse_number_with_range("100 TO 200") == 100.0

    def test_range_parsing_german_format(self, extractor):
        """Test German number format in ranges."""
        # Thousands separator
        assert extractor.parse_number_with_range("100.000-150.000") == 100000.0

        # Decimal comma
        assert extractor.parse_number_with_range("2,5-3,5") == 2.5

        # Large number with decimal (single value, not range)
        assert extractor.parse_number_with_range("100.000,50") == 100000.5

    def test_range_parsing_single_number(self, extractor):
        """Test that single numbers (no range) still work."""
        assert extractor.parse_number_with_range("50") == 50.0
        assert extractor.parse_number_with_range("100.000") == 100000.0
        assert extractor.parse_number_with_range("2,5") == 2.5

    def test_range_parsing_invalid_range(self, extractor):
        """Test invalid ranges (lower >= upper) fall back to first number."""
        result = extractor.parse_number_with_range("200-100")
        assert result == 200.0  # Falls back to first number

    def test_range_parsing_empty_or_none(self, extractor):
        """Test empty string and None."""
        assert extractor.parse_number_with_range("") is None
        assert extractor.parse_number_with_range(None) is None

    def test_range_parsing_non_numeric(self, extractor):
        """Test non-numeric strings."""
        assert extractor.parse_number_with_range("foo") is None
        assert extractor.parse_number_with_range("abc-def") is None


class TestRangeParsingIntegration:
    """Test range parsing integrated with extract_from_html."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing."""
        return AustrianRealEstateExtractor()

    def test_extract_size_with_range(self, extractor):
        """Test extracting size from HTML with range."""
        html = """
        <div>Wohnfläche: 40-140 m²</div>
        """
        extracted = extractor.extract_from_html(html)
        assert extracted["size_sqm"] == 40.0  # Lower bound

    def test_extract_rooms_with_range(self, extractor):
        """Test extracting rooms with range."""
        html = """
        <div>2-3 Zimmer</div>
        """
        extracted = extractor.extract_from_html(html)
        assert extracted["rooms"] == 2.0  # Lower bound

    def test_extract_price_with_range(self, extractor):
        """Test extracting price with range."""
        html = """
        <div>Kaufpreis: €100.000-150.000</div>
        """
        extracted = extractor.extract_from_html(html)
        assert extracted["price"] == 100000.0  # Lower bound

    def test_extract_betriebskosten_with_range(self, extractor):
        """Test extracting betriebskosten with range."""
        html = """
        <div>Betriebskosten: €100-200 monatlich</div>
        """
        extracted = extractor.extract_from_html(html)
        assert extracted["betriebskosten_monthly"] == 100.0  # Lower bound

    def test_extract_no_range(self, extractor):
        """Test that single values (no range) still work."""
        html = """
        <div>Wohnfläche: 65 m²</div>
        <div>3 Zimmer</div>
        <div>Kaufpreis: €120.000</div>
        <div>Betriebskosten: €150 monatlich</div>
        """
        extracted = extractor.extract_from_html(html)

        assert extracted["size_sqm"] == 65.0
        assert extracted["rooms"] == 3.0
        assert extracted["price"] == 120000.0
        assert extracted["betriebskosten_monthly"] == 150.0

    def test_extract_mixed_ranges_and_singles(self, extractor):
        """Test HTML with both ranges and single values."""
        html = """
        <div>Wohnfläche: 40-60 m²</div>
        <div>3 Zimmer</div>
        <div>Kaufpreis: €120.000</div>
        <div>Betriebskosten: €100-150 monatlich</div>
        """
        extracted = extractor.extract_from_html(html)

        assert extracted["size_sqm"] == 40.0  # Range - lower bound
        assert extracted["rooms"] == 3.0  # Single value
        assert extracted["price"] == 120000.0  # Single value
        assert extracted["betriebskosten_monthly"] == 100.0  # Range - lower bound


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
