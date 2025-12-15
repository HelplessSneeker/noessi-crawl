"""ImmobilienScout24.at portal adapter (PLACEHOLDER)."""

import logging
from typing import Any, Dict, List, Optional

from portals.base import PortalAdapter

logger = logging.getLogger(__name__)


class ImmoscoutAdapter(PortalAdapter):
    """
    Adapter for ImmobilienScout24.at (PLACEHOLDER - requires research).

    This is a placeholder implementation that returns safe defaults.
    All methods log warnings and return empty/safe values.

    To implement:
    1. Research ImmobilienScout24.at website structure
    2. Document URL patterns, listing extraction, and ad filtering
    3. Implement all abstract methods with actual logic
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize placeholder adapter."""
        super().__init__(config)
        self.postal_codes = config.get("postal_codes", [])
        logger.warning(
            "ImmoscoutAdapter is a PLACEHOLDER - no actual scraping will occur. "
            "Research and implementation required."
        )

    def get_portal_name(self) -> str:
        """Return portal identifier."""
        return "immoscout"

    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize config (placeholder - no changes)."""
        return config.copy()

    def build_search_url(self, page: int = 1, **kwargs) -> str:
        """
        Build search URL (PLACEHOLDER).

        TODO: Research actual ImmobilienScout24 URL structure.
        Expected format (UNVERIFIED):
        - https://www.immobilienscout24.at/regional/wien/wohnung-kaufen?...
        - https://www.immobilienscout24.at/suche?postcodes=1010,1020&...
        """
        base_url = "https://www.immobilienscout24.at/placeholder"
        logger.warning(
            f"ImmoscoutAdapter.build_search_url() is PLACEHOLDER - "
            f"returning dummy URL: {base_url}"
        )
        return base_url

    def extract_listing_urls(self, html: str) -> List[Dict[str, str]]:
        """
        Extract listing URLs (PLACEHOLDER).

        TODO: Research extraction method.
        Possible approaches:
        1. JSON-LD structured data (preferred if available)
        2. CSS selectors for listing cards
        3. data-* attributes
        """
        logger.warning(
            "ImmoscoutAdapter.extract_listing_urls() is PLACEHOLDER - "
            "returning empty list"
        )
        return []

    def extract_listing_id(self, url: str) -> str:
        """
        Extract listing ID (PLACEHOLDER).

        TODO: Research actual URL format.
        Expected patterns:
        - /expose/12345678
        - /detail/12345678
        """
        logger.warning(
            f"ImmoscoutAdapter.extract_listing_id() is PLACEHOLDER - "
            f"returning hash: {hash(url)}"
        )
        return str(hash(url))

    def should_filter_ad(self, html: str) -> bool:
        """
        Check if listing is ad (PLACEHOLDER).

        TODO: Research ad/sponsored listing indicators.
        Possible markers:
        - CSS class "sponsored" or "premium"
        - data-ad="true"
        - Badge text
        """
        logger.warning(
            "ImmoscoutAdapter.should_filter_ad() is PLACEHOLDER - "
            "returning False (no filtering)"
        )
        return False

    def extract_address_from_html(self, html: str, url: str) -> Optional[str]:
        """
        Extract address (PLACEHOLDER).

        TODO: Research address extraction methods.
        Possible sources:
        - JSON-LD address field
        - HTML elements with specific classes
        - Meta tags
        """
        logger.warning(
            "ImmoscoutAdapter.extract_address_from_html() is PLACEHOLDER - "
            "returning None"
        )
        return None
