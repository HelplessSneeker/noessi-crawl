"""Unit tests for portal adapters."""

import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from typing import Dict, Any
from portals import get_adapter
from portals.base import PortalAdapter
from portals.willhaben.adapter import WillhabenAdapter
from portals.immoscout.adapter import ImmoscoutAdapter


class TestWillhabenAdapter:
    """Test WillhabenAdapter functionality."""

    def test_postal_code_translation(self):
        """Test postal code to area_id translation."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010", "1020", "9020"],
            "filters": {}
        }
        adapter = WillhabenAdapter(config)

        # Vienna 1st district (1010) -> area_id 201
        # Vienna 2nd district (1020) -> area_id 202
        # Klagenfurt (9020) -> area_id 117223
        assert 201 in adapter.area_ids
        assert 202 in adapter.area_ids
        assert 117223 in adapter.area_ids
        assert len(adapter.area_ids) == 3

    def test_legacy_area_ids_support(self):
        """Test backward compatibility with legacy area_ids config."""
        config = {
            "portal": "willhaben",
            "area_ids": [900, 201, 401],
            "filters": {}
        }
        adapter = WillhabenAdapter(config)

        assert adapter.area_ids == [900, 201, 401]
        assert len(adapter.area_ids) == 3

    def test_url_building_basic(self):
        """Test basic URL construction."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010", "1020"],
            "filters": {}
        }
        adapter = WillhabenAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "willhaben.at" in url
        assert "areaId=201" in url  # 1010
        assert "areaId=202" in url  # 1020
        assert "page=1" in url

    def test_url_building_with_price_filter(self):
        """Test URL construction with price filter."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "filters": {"max_price": 150000}
        }
        adapter = WillhabenAdapter(config)
        url = adapter.build_search_url(page=1)

        assert "PRICE_TO=150000" in url
        assert "areaId=201" in url

    def test_url_building_pagination(self):
        """Test URL pagination."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "filters": {}
        }
        adapter = WillhabenAdapter(config)

        url_page1 = adapter.build_search_url(page=1)
        url_page2 = adapter.build_search_url(page=2)

        assert "page=1" in url_page1
        assert "page=2" in url_page2

    def test_listing_id_extraction(self):
        """Test listing ID extraction from URLs."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        # Test standard URL format
        url1 = "https://www.willhaben.at/iad/immobilien/d/wohnung/1234567890"
        assert adapter.extract_listing_id(url1) == "1234567890"

        # Test URL with trailing slash
        url2 = "https://www.willhaben.at/iad/immobilien/d/wohnung/9876543210/"
        assert adapter.extract_listing_id(url2) == "9876543210"

        # Test URL without numeric ID falls back to hash
        url3 = "https://www.willhaben.at/iad/immobilien/d/wohnung/no-id-here"
        listing_id = adapter.extract_listing_id(url3)
        assert isinstance(listing_id, str)
        assert len(listing_id) > 0  # Hash should be non-empty

    def test_should_filter_ad_real_listing(self):
        """Test ad filtering with star icon present (real listing)."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        # HTML with star icon = real listing, should NOT filter
        html_with_star = """
        <html>
            <svg><path d="m12 4 2.09 4.25a1.52 1.52 0 0 0 1.14.82l4.64.64-3.42 3.32"></path></svg>
        </html>
        """
        assert adapter.should_filter_ad(html_with_star) is False

    def test_should_filter_ad_promoted(self):
        """Test ad filtering with star icon absent (promoted ad)."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        # HTML without star icon = promoted ad, SHOULD filter
        html_without_star = """
        <html>
            <div class="listing">Some content</div>
        </html>
        """
        assert adapter.should_filter_ad(html_without_star) is True

    def test_get_portal_name(self):
        """Test portal name identifier."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        assert adapter.get_portal_name() == "willhaben"

    def test_extract_listing_urls(self):
        """Test extraction of listing URLs from JSON-LD ItemList."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        # Sample HTML with ItemList JSON-LD (actual willhaben format - compact JSON)
        html = '''<html><script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"url":"/iad/immobilien/d/wohnung/1234567890"},{"url":"/iad/immobilien/d/wohnung/9876543210"}]}</script></html>'''

        listings = adapter.extract_listing_urls(html)
        assert len(listings) == 2
        assert any("1234567890" in listing["url"] for listing in listings)
        assert any("9876543210" in listing["url"] for listing in listings)

    def test_extract_address_from_html(self):
        """Test address extraction from HTML."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = WillhabenAdapter(config)

        # Test with JSON-LD address containing street name
        html_with_jsonld = """
        <script type="application/ld+json">
        {
            "@type": "Product",
            "address": {
                "streetAddress": "Stephansplatz 1, 1010 Wien"
            }
        }
        </script>
        """

        url = "https://www.willhaben.at/iad/immobilien/d/wohnung/1234567890"
        address = adapter.extract_address_from_html(html_with_jsonld, url)

        # Should extract streetAddress
        assert address is not None
        assert "Stephansplatz" in address or "platz" in address.lower()


class TestImmoscoutAdapter:
    """Test ImmoscoutAdapter placeholder functionality."""

    def test_instantiation(self):
        """Test adapter can be instantiated."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        assert adapter is not None
        assert isinstance(adapter, PortalAdapter)

    def test_placeholder_returns_safe_defaults(self):
        """Test placeholder methods return safe defaults."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        # Test all methods return safe defaults
        assert adapter.get_portal_name() == "immoscout"
        assert "immobilienscout24.at" in adapter.build_search_url(page=1)
        assert adapter.extract_listing_urls("<html></html>") == []

        # extract_listing_id falls back to hash for placeholder
        listing_id = adapter.extract_listing_id("https://example.com/123")
        assert isinstance(listing_id, str)
        assert len(listing_id) > 0  # Hash should be non-empty

        assert adapter.should_filter_ad("<html></html>") is False
        assert adapter.extract_address_from_html("<html></html>", "https://example.com") is None

    def test_placeholder_logs_warnings(self, caplog):
        """Test adapter logs informational messages (no longer placeholder)."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = ImmoscoutAdapter(config)

        # Call various methods
        adapter.build_search_url(page=1)
        adapter.extract_listing_urls("<html></html>")

        # Check that warnings/info were logged (BEST EFFORT, not PLACEHOLDER)
        # The adapter should log warnings about extraction failures or URL structure
        assert any("BEST EFFORT" in record.message or "educated guess" in record.message.lower()
                   or "Failed to extract" in record.message
                   for record in caplog.records)


class TestPortalFactory:
    """Test portal adapter factory function."""

    def test_get_willhaben_adapter(self):
        """Test factory returns WillhabenAdapter."""
        config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {}}
        adapter = get_adapter(config)

        assert isinstance(adapter, WillhabenAdapter)
        assert adapter.get_portal_name() == "willhaben"

    def test_get_immoscout_adapter(self):
        """Test factory returns ImmoscoutAdapter."""
        config = {"portal": "immoscout", "filters": {}}
        adapter = get_adapter(config)

        assert isinstance(adapter, ImmoscoutAdapter)
        assert adapter.get_portal_name() == "immoscout"

    def test_default_portal_is_willhaben(self):
        """Test default portal is willhaben when not specified."""
        config = {"postal_codes": ["1010"], "filters": {}}  # No portal specified
        adapter = get_adapter(config)

        assert isinstance(adapter, WillhabenAdapter)
        assert adapter.get_portal_name() == "willhaben"

    def test_invalid_portal_raises_error(self):
        """Test invalid portal raises ValueError."""
        config = {"portal": "invalid_portal", "filters": {}}

        with pytest.raises(ValueError, match="Unsupported portal"):
            get_adapter(config)

    def test_case_insensitive_portal_selection(self):
        """Test portal selection is case-insensitive."""
        config1 = {"portal": "WILLHABEN", "postal_codes": ["1010"], "filters": {}}
        config2 = {"portal": "WillHaben", "postal_codes": ["1010"], "filters": {}}
        config3 = {"portal": "Immoscout", "filters": {}}

        adapter1 = get_adapter(config1)
        adapter2 = get_adapter(config2)
        adapter3 = get_adapter(config3)

        assert isinstance(adapter1, WillhabenAdapter)
        assert isinstance(adapter2, WillhabenAdapter)
        assert isinstance(adapter3, ImmoscoutAdapter)
