"""Basic tests for ImmoscoutAdapter implementation."""

import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from portals.immoscout.adapter import ImmoscoutAdapter


class TestImmoscoutURLBuilding:
    """Test URL building with various parameters."""

    def test_basic_url_no_filters(self):
        """Test basic URL with just postal codes (single)."""
        config = {"portal": "immoscout", "postal_codes": ["1010"], "filters": {}}
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "immobilienscout24.at" in url
        assert "/regional/1010/wohnung-kaufen" in url

    def test_url_with_multiple_postal_codes(self):
        """Test URL with multiple postal codes."""
        config = {"portal": "immoscout", "postal_codes": ["1010", "1020", "9020"], "filters": {}}
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "/regional/wohnung-kaufen" in url
        assert "countryCode=AT" in url
        assert "zipCode=1010,1020,9020" in url

    def test_url_with_price_filter(self):
        """Test URL with max price filter."""
        config = {
            "portal": "immoscout",
            "postal_codes": ["1010"],
            "filters": {"max_price": 150000}
        }
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "primaryPriceTo=150000" in url

    def test_url_with_size_filters(self):
        """Test URL with size filters."""
        config = {
            "portal": "immoscout",
            "postal_codes": ["1010"],
            "filters": {"min_size_sqm": 40, "max_size_sqm": 100}
        }
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "primaryAreaFrom=40" in url
        assert "primaryAreaTo=100" in url

    def test_url_with_pagination(self):
        """Test URL with pagination."""
        config = {"portal": "immoscout", "postal_codes": ["1010"], "filters": {}}
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=2)

        assert "pageNumber=2" in url

    def test_url_with_all_filters(self):
        """Test URL with all filters combined (multiple postal codes)."""
        config = {
            "portal": "immoscout",
            "postal_codes": ["1010", "1020"],
            "filters": {
                "max_price": 150000,
                "min_size_sqm": 40,
                "max_size_sqm": 100
            }
        }
        adapter = ImmoscoutAdapter(config)
        url = adapter.build_search_url(page=3)

        assert "/regional/wohnung-kaufen" in url
        assert "countryCode=AT" in url
        assert "zipCode=1010,1020" in url
        assert "primaryPriceTo=150000" in url
        assert "primaryAreaFrom=40" in url
        assert "primaryAreaTo=100" in url
        assert "pageNumber=3" in url


class TestListingIDExtraction:
    """Test listing ID extraction from various URL formats."""

    def test_extract_from_expose_url(self):
        """Test extraction from /expose/ URL."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/expose/12345678"
        listing_id = adapter.extract_listing_id(url)
        assert listing_id == "12345678"

    def test_extract_from_detail_url(self):
        """Test extraction from /detail/ URL."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/detail/98765432"
        listing_id = adapter.extract_listing_id(url)
        assert listing_id == "98765432"

    def test_extract_from_immobilie_url(self):
        """Test extraction from /immobilie/ URL."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/immobilie/11223344"
        listing_id = adapter.extract_listing_id(url)
        assert listing_id == "11223344"

    def test_extract_with_trailing_slash(self):
        """Test extraction with trailing slash."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/expose/12345678/"
        listing_id = adapter.extract_listing_id(url)
        assert listing_id == "12345678"

    def test_extract_with_query_params(self):
        """Test extraction with query parameters."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/expose/12345678?ref=search"
        listing_id = adapter.extract_listing_id(url)
        assert listing_id == "12345678"

    def test_fallback_to_hash(self):
        """Test fallback to hash for unknown URL format."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/weird/path/format"
        listing_id = adapter.extract_listing_id(url)

        # Should return a hash (numeric string)
        assert listing_id.isdigit()
        assert len(listing_id) > 5


class TestAdFiltering:
    """Test sponsored ad filtering."""

    def test_filter_premium_class(self):
        """Test filtering with premium class."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '<div class="listing premium">Test</div>'
        assert adapter.should_filter_ad(html) is True

    def test_filter_sponsored_class(self):
        """Test filtering with sponsored class."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '<div class="result-item sponsored">Test</div>'
        assert adapter.should_filter_ad(html) is True

    def test_filter_data_premium(self):
        """Test filtering with data-premium attribute."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '<article data-premium="true">Test</article>'
        assert adapter.should_filter_ad(html) is True

    def test_no_filter_regular_listing(self):
        """Test keeping regular listings."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '<div class="listing">Regular listing</div>'
        assert adapter.should_filter_ad(html) is False


class TestAddressExtraction:
    """Test address extraction from various sources."""

    def test_extract_from_url(self):
        """Test extraction from URL path."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        url = "https://www.immobilienscout24.at/wien-1030-landstrasse/expose/12345"
        html = "<html><body>No address in HTML</body></html>"

        address = adapter.extract_address_from_html(html, url)
        # Should extract location from URL
        assert address is not None
        assert "Wien" in address or "1030" in address or "Landstrasse" in address

    def test_extract_from_html_pattern(self):
        """Test extraction from HTML with address class."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '<div class="property-address">Teststraße 123, 1010 Wien</div>'
        url = "https://www.immobilienscout24.at/expose/12345"

        address = adapter.extract_address_from_html(html, url)
        assert address == "Teststraße 123, 1010 Wien"

    def test_extract_from_json_ld(self):
        """Test extraction from JSON-LD structured data."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = '''
        <script type="application/ld+json">
        {
            "@type": "RealEstateListing",
            "address": {
                "streetAddress": "Testgasse 45",
                "postalCode": "1020",
                "addressLocality": "Wien"
            }
        }
        </script>
        '''
        url = "https://www.immobilienscout24.at/expose/12345"

        address = adapter.extract_address_from_html(html, url)
        assert address is not None
        assert "Testgasse 45" in address
        assert "1020" in address
        assert "Wien" in address

    def test_no_address_found(self):
        """Test graceful handling when no address found."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        html = "<html><body>No address here</body></html>"
        url = "https://www.immobilienscout24.at/12345"

        address = adapter.extract_address_from_html(html, url)
        assert address is None


class TestConfigNormalization:
    """Test configuration normalization."""

    def test_postal_codes_as_list(self):
        """Test postal codes remain as list."""
        config = {"portal": "immoscout", "postal_codes": ["1010", "1020"], "filters": {}}
        adapter = ImmoscoutAdapter(config)
        normalized = adapter.normalize_config(config)

        assert isinstance(normalized["postal_codes"], list)
        assert normalized["postal_codes"] == ["1010", "1020"]

    def test_postal_codes_single_value(self):
        """Test single postal code converted to list."""
        config = {"portal": "immoscout", "postal_codes": "1010", "filters": {}}
        adapter = ImmoscoutAdapter(config)
        normalized = adapter.normalize_config(config)

        assert isinstance(normalized["postal_codes"], list)
        assert normalized["postal_codes"] == ["1010"]


class TestCrawlerConfig:
    """Test crawler configuration."""

    def test_detail_page_config(self):
        """Test detail page crawler config."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)
        crawler_config = adapter.get_crawler_config()

        assert "wait_for" in crawler_config
        assert "delay_before_return_html" in crawler_config
        assert "timeout" in crawler_config
        assert crawler_config["delay_before_return_html"] >= 1000  # At least 1 second

    def test_search_page_config(self):
        """Test search page crawler config."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)
        search_config = adapter.get_search_crawler_config()

        assert "wait_for" in search_config
        assert "delay_before_return_html" in search_config
        assert "timeout" in search_config


class TestBasicProperties:
    """Test basic adapter properties."""

    def test_get_portal_name(self):
        """Test portal name is correct."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        assert adapter.get_portal_name() == "immoscout"

    def test_postal_codes_stored(self):
        """Test postal codes are stored correctly."""
        config = {"portal": "immoscout", "postal_codes": ["1010", "1020"], "filters": {}}
        adapter = ImmoscoutAdapter(config)

        assert adapter.postal_codes == ["1010", "1020"]
