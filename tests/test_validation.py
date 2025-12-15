"""Unit tests for critical field validation."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from models.apartment import ApartmentListing
from main import EnhancedApartmentScraper
from portals import get_adapter


class TestCriticalFieldValidation:
    """Test validation of critical fields."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance for testing."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "extraction": {"use_llm": False},
            "output": {"summary_top_n": 20}
        }
        adapter = get_adapter(config)
        return EnhancedApartmentScraper(config, adapter)

    def test_validation_all_fields_present(self, scraper):
        """Test validation passes when all critical fields present."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=100000,
            size_sqm=50,
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is True
        assert reason is None

    def test_validation_missing_price(self, scraper):
        """Test validation fails when price is missing."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=None,  # MISSING
            size_sqm=50,
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "price" in reason

    def test_validation_missing_size(self, scraper):
        """Test validation fails when size_sqm is missing."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=100000,
            size_sqm=None,  # MISSING
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "size_sqm" in reason

    def test_validation_missing_betriebskosten(self, scraper):
        """Test validation fails when betriebskosten is missing."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=100000,
            size_sqm=50,
            betriebskosten_monthly=None  # MISSING
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "betriebskosten_monthly" in reason

    def test_validation_multiple_missing(self, scraper):
        """Test validation fails with multiple missing fields."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=None,  # MISSING
            size_sqm=None,  # MISSING
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "price" in reason
        assert "size_sqm" in reason
        assert "betriebskosten_monthly" not in reason

    def test_validation_zero_price(self, scraper):
        """Test validation treats zero price as invalid."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=0,  # INVALID (treated as missing)
            size_sqm=50,
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "price" in reason

    def test_validation_negative_size(self, scraper):
        """Test validation treats negative size as invalid."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=100000,
            size_sqm=-10,  # INVALID
            betriebskosten_monthly=150
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "size_sqm" in reason

    def test_validation_zero_betriebskosten(self, scraper):
        """Test validation treats zero betriebskosten as invalid."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=100000,
            size_sqm=50,
            betriebskosten_monthly=0  # INVALID
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "betriebskosten_monthly" in reason

    def test_validation_all_missing(self, scraper):
        """Test validation fails when all critical fields missing."""
        apt = ApartmentListing(
            listing_id="123",
            source_url="https://example.com",
            source_portal="willhaben",
            price=None,
            size_sqm=None,
            betriebskosten_monthly=None
        )

        is_valid, reason = scraper._validate_critical_fields(apt)
        assert is_valid is False
        assert "price" in reason
        assert "size_sqm" in reason
        assert "betriebskosten_monthly" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
