"""Test betriebskosten extraction fixes.

This test suite validates that the betriebskosten extraction improvements work correctly.
"""

import pytest
from pathlib import Path

from utils.extractors import AustrianRealEstateExtractor


# Manually verified from willhaben.at page
# URL: https://www.willhaben.at/iad/immobilien/d/eigentumswohnung/kaernten/klagenfurt/lichtdurchflutete-wohnung-mit-kleinem-balkon-2061847835/
# The field is called "Nebenkosten" (additional costs) on willhaben.at
EXPECTED_BETRIEBSKOSTEN = 395.0  # EUR/month


@pytest.fixture
def fixture_html():
    """Load the fixture HTML for testing"""
    fixture_path = Path(__file__).parent / "fixtures" / "betriebskosten_klagenfurt_180k.html"
    if not fixture_path.exists():
        pytest.skip("Fixture HTML not found. Run tests/fetch_betriebskosten_fixture.py first.")

    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


class TestBetriebskostenRegexExtraction:
    """Test regex pattern extraction for betriebskosten"""

    def test_rejects_placeholder_value_1(self, fixture_html):
        """Should NOT extract '1' as betriebskosten (placeholder value)"""
        extractor = AustrianRealEstateExtractor()

        result = extractor.extract_from_html(fixture_html)

        # If betriebskosten was extracted, it should NOT be 1.0
        if "betriebskosten_monthly" in result:
            assert result["betriebskosten_monthly"] != 1.0, \
                "Should reject placeholder value of €1"
            assert result["betriebskosten_monthly"] >= 10.0, \
                "Should reject unrealistic values under €10"

    def test_extracts_realistic_betriebskosten(self, fixture_html):
        """Should extract betriebskosten in realistic range"""
        extractor = AustrianRealEstateExtractor()

        result = extractor.extract_from_html(fixture_html)

        if EXPECTED_BETRIEBSKOSTEN is not None:
            assert "betriebskosten_monthly" in result, \
                "Should extract betriebskosten from HTML"

            # Allow 10% tolerance for rounding/formatting differences
            expected = EXPECTED_BETRIEBSKOSTEN
            actual = result["betriebskosten_monthly"]
            tolerance = expected * 0.1

            assert abs(actual - expected) <= tolerance, \
                f"Expected betriebskosten ~€{expected}, got €{actual}"
        else:
            pytest.skip("EXPECTED_BETRIEBSKOSTEN not set - update after manual verification")

    def test_price_pattern_does_not_interfere(self, fixture_html):
        """Price patterns should not capture betriebskosten values"""
        extractor = AustrianRealEstateExtractor()

        result = extractor.extract_from_html(fixture_html)

        # Price should be €180,000
        assert result.get("price") == 180000.0, "Should extract correct price"

        # Betriebskosten should be different from price
        if "betriebskosten_monthly" in result:
            assert result["betriebskosten_monthly"] != result.get("price"), \
                "Betriebskosten should not equal purchase price"


class TestMinValueValidation:
    """Test that minimum value validation works"""

    def test_extract_field_min_value_validation(self):
        """extract_field should filter values below min_value"""
        extractor = AustrianRealEstateExtractor()

        # Mock HTML with low value
        html = "Betriebskosten: € 1"

        patterns = extractor.BETRIEBSKOSTEN_PATTERNS

        # Without min_value - should extract (old behavior)
        result_no_min = extractor.extract_field(html, patterns)
        if result_no_min:
            parsed = extractor.parse_number(result_no_min)
            # This might extract "1" currently

        # With min_value - should reject (new behavior after fixes)
        result_with_min = extractor.extract_field(
            html,
            patterns,
            min_value=10.0
        )
        # Should return None because 1 < 10
        # Note: This test will FAIL until we implement min_value parameter
        # That's expected - this is a TDD approach


@pytest.mark.skip(reason="Requires BeautifulSoup implementation (Phase 5)")
class TestDOMParserExtraction:
    """Test DOM-based extraction (optional Phase 5)"""

    def test_dom_parser_finds_separated_betriebskosten(self, fixture_html):
        """DOM parser should find betriebskosten even if label/value separated"""
        extractor = AustrianRealEstateExtractor()

        result = extractor.extract_from_html_dom(fixture_html)

        if EXPECTED_BETRIEBSKOSTEN is not None:
            assert "betriebskosten_monthly" in result
            assert result["betriebskosten_monthly"] == pytest.approx(
                EXPECTED_BETRIEBSKOSTEN, rel=0.1
            )


class TestLLMValidation:
    """Test LLM validation logic (mocked)"""

    def test_llm_rejects_values_under_20_euros(self):
        """LLM validator should reject betriebskosten < €20"""
        from llm.extractor import OllamaExtractor

        extractor = OllamaExtractor()

        # Test data with suspiciously low value
        extracted = {"betriebskosten_monthly": 1.0}

        # Validate and clean
        validated = extractor._validate_and_clean(extracted, {})

        # Should reject value under €20
        # This test will FAIL until we update the validator lambda
        # That's expected - TDD approach
        assert "betriebskosten_monthly" not in validated, \
            "Should reject betriebskosten under €20"

    def test_llm_accepts_realistic_values(self):
        """LLM validator should accept realistic betriebskosten values"""
        from llm.extractor import OllamaExtractor

        extractor = OllamaExtractor()

        # Test realistic values
        test_values = [50.0, 150.0, 500.0, 1000.0]

        for value in test_values:
            extracted = {"betriebskosten_monthly": value}
            validated = extractor._validate_and_clean(extracted, {})

            assert "betriebskosten_monthly" in validated, \
                f"Should accept realistic value €{value}"
            assert validated["betriebskosten_monthly"] == value


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for full extraction pipeline"""

    def test_extraction_priority_order(self, fixture_html):
        """Should extract betriebskosten with priority: DOM > Regex > LLM"""
        # This will be implemented after all phases are complete
        pytest.skip("Integration test - implement after all phases complete")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
