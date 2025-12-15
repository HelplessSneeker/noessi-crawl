"""Backward compatibility tests for portal adapter refactoring."""

import sys
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from typing import Dict, Any
from portals import get_adapter
from portals.willhaben.adapter import WillhabenAdapter


class TestBackwardCompatibility:
    """Test backward compatibility with legacy configurations."""

    def test_postal_codes_config_format(self):
        """Test new postal_codes config format works correctly."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010", "1020", "9020"],
            "filters": {"max_price": 150000}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Verify postal codes were translated to area_ids
        assert 201 in adapter.area_ids  # 1010
        assert 202 in adapter.area_ids  # 1020
        assert 117223 in adapter.area_ids  # 9020

        # Verify URL building works
        url = adapter.build_search_url(page=1)
        assert "areaId=201" in url
        assert "areaId=202" in url
        assert "areaId=117223" in url
        assert "PRICE_TO=150000" in url

    def test_legacy_area_ids_config_format(self):
        """Test legacy area_ids config format still works."""
        config = {
            "portal": "willhaben",
            "area_ids": [900, 201, 401],  # Legacy format
            "filters": {"max_price": 150000}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Verify area_ids are used directly
        assert adapter.area_ids == [900, 201, 401]

        # Verify URL building works
        url = adapter.build_search_url(page=1)
        assert "areaId=900" in url
        assert "areaId=201" in url
        assert "areaId=401" in url
        assert "PRICE_TO=150000" in url

    def test_no_postal_codes_or_area_ids(self):
        """Test graceful handling when neither postal_codes nor area_ids provided."""
        config = {
            "portal": "willhaben",
            "filters": {}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Should have empty area_ids list
        assert adapter.area_ids == []

        # URL building should still work (though without area filters)
        url = adapter.build_search_url(page=1)
        assert "willhaben.at" in url

    def test_config_with_all_original_fields(self):
        """Test config with all original fields works correctly."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010", "1020"],
            "output_folder": "output",
            "max_pages": 1,
            "filters": {
                "min_yield": None,
                "max_price": 150000,
                "min_size_sqm": None,
                "max_size_sqm": None,
                "excluded_districts": [],
                "max_betriebskosten_per_sqm": None,
                "exclude_renovierung_needed": False,
                "exclude_poor_energy": False,
                "min_investment_score": None
            },
            "analysis": {
                "mortgage_rate": 3.5,
                "down_payment_percent": 10,
                "transaction_cost_percent": 9,
                "loan_term_years": 30
            },
            "output": {
                "generate_summary": True,
                "pdf_top_n": 20,
                "generate_pdf": True,
                "pdf_filename": "investment_summary.pdf"
            },
            "rate_limiting": {
                "delay_apartment": 0.5,
                "delay_page": 1.0
            },
            "llm_settings": {
                "enabled": True,
                "model": "qwen2.5:14b",
                "generate_summary": True
            }
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Verify adapter initialized correctly
        assert 201 in adapter.area_ids  # 1010
        assert 202 in adapter.area_ids  # 1020

        # Verify filters are accessible
        assert adapter.filters["max_price"] == 150000

    def test_unknown_postal_code_logs_warning(self, caplog):
        """Test unknown postal code logs warning but doesn't crash."""
        import logging

        # Clear any previous log records and set level to capture warnings
        caplog.clear()
        caplog.set_level(logging.WARNING)

        config = {
            "portal": "willhaben",
            "postal_codes": ["1010", "9999"],  # 9999 is not in PLZ_TO_AREA_ID
            "filters": {}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Should have translated known postal code
        assert 201 in adapter.area_ids  # 1010

        # Should log warning for unknown postal code
        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("9999" in msg for msg in warning_messages)

    def test_mixed_config_postal_codes_and_area_ids(self):
        """Test behavior when both postal_codes and area_ids are provided."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "area_ids": [202, 117223],  # Should be ignored in favor of postal_codes
            "filters": {}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # postal_codes should take precedence
        assert 201 in adapter.area_ids  # from 1010
        # area_ids should be ignored when postal_codes is present
        assert 202 not in adapter.area_ids
        assert 117223 not in adapter.area_ids

    def test_empty_postal_codes_list(self):
        """Test empty postal_codes list is handled gracefully."""
        config = {
            "portal": "willhaben",
            "postal_codes": [],
            "filters": {}
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)
        assert adapter.area_ids == []

    def test_filters_passed_to_adapter(self):
        """Test filters from config are accessible in adapter."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "filters": {
                "max_price": 200000,
                "min_size_sqm": 40,
                "excluded_districts": [10, 11]
            }
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)

        # Verify filters are stored in adapter
        assert adapter.filters["max_price"] == 200000
        assert adapter.filters["min_size_sqm"] == 40
        assert adapter.filters["excluded_districts"] == [10, 11]

        # Verify max_price is used in URL building
        url = adapter.build_search_url(page=1)
        assert "PRICE_TO=200000" in url

    def test_config_without_portal_defaults_to_willhaben(self):
        """Test config without portal field defaults to willhaben."""
        config = {
            "postal_codes": ["1010"],
            "filters": {}
            # No "portal" field
        }

        adapter = get_adapter(config)
        assert isinstance(adapter, WillhabenAdapter)
        assert adapter.get_portal_name() == "willhaben"

    def test_crawler_config_compatibility(self):
        """Test crawler config methods return expected format."""
        config = {
            "portal": "willhaben",
            "postal_codes": ["1010"],
            "filters": {}
        }

        adapter = get_adapter(config)

        # Test detail page crawler config
        detail_config = adapter.get_crawler_config()
        assert isinstance(detail_config, dict)
        assert "wait_for" in detail_config or "delay_before_return_html" in detail_config

        # Test search page crawler config
        search_config = adapter.get_search_crawler_config()
        assert isinstance(search_config, dict)
        assert "wait_for" in search_config or "delay_before_return_html" in search_config
