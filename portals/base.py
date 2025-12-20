"""Abstract base class for portal-specific adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PortalAdapter(ABC):
    """
    Abstract base class for real estate portal adapters.

    Each portal (Willhaben, ImmobilienScout24, etc.) implements this interface
    to handle portal-specific logic like URL building, listing extraction, and
    ad filtering.

    Portal-agnostic logic (Austrian address parsing, investment analysis, LLM
    extraction, output generation) remains in shared utility modules.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration.

        Args:
            config: Full configuration dictionary from config.json
        """
        self.config = config
        self.filters = config.get("filters", {})

    @abstractmethod
    def get_portal_name(self) -> str:
        """
        Return portal identifier.

        Returns:
            Portal name (e.g., "willhaben", "immoscout")
        """
        pass

    @abstractmethod
    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate portal-agnostic config to portal-specific format.

        Example: Convert postal_codes to Willhaben area_ids

        Args:
            config: Original configuration dictionary

        Returns:
            Normalized configuration with portal-specific fields
        """
        pass

    @abstractmethod
    def build_search_url(self, page: int = 1, **kwargs) -> str:
        """
        Build search URL for listing results page.

        Args:
            page: Page number (1-indexed)
            **kwargs: Additional portal-specific parameters

        Returns:
            Full search URL with filters and pagination

        Example:
            https://www.willhaben.at/iad/immobilien/...?areaId=201&page=1
        """
        pass

    @abstractmethod
    def extract_listing_urls(self, html: str) -> List[Dict[str, str]]:
        """
        Extract apartment listing URLs from search results page.

        Args:
            html: Search results page HTML

        Returns:
            List of dicts with 'url' key
            Example: [{"url": "https://..."}, {"url": "https://..."}]
        """
        pass

    @abstractmethod
    def extract_listing_id(self, url: str) -> str:
        """
        Extract unique listing ID from apartment URL.

        Args:
            url: Apartment listing URL

        Returns:
            Unique listing ID (string)

        Example:
            URL: https://willhaben.at/.../12345678
            Returns: "12345678"
        """
        pass

    @abstractmethod
    def should_filter_ad(self, html: str) -> bool:
        """
        Determine if listing is a promoted/sponsored ad to filter out.

        Args:
            html: Apartment detail page HTML

        Returns:
            True if listing should be filtered (is an ad), False otherwise
        """
        pass

    @abstractmethod
    def extract_address_from_html(self, html: str, url: str) -> Optional[str]:
        """
        Extract raw address text from HTML or URL.

        Portal-specific extraction only. Actual parsing is done by
        AustrianAddressParser (portal-agnostic).

        Args:
            html: Apartment detail page HTML
            url: Apartment URL (may contain address info)

        Returns:
            Raw address string or None

        Example:
            "Landstraßer Hauptstraße 1, 1030 Wien"
        """
        pass

    def get_crawler_config(self) -> Dict[str, Any]:
        """
        Get portal-specific crawler configuration for detail pages.

        Returns:
            Dict with crawl4ai configuration parameters

        Default implementation:
            {"wait_for": "css:main", "delay_before_return_html": 2.0}
        """
        return {
            "wait_for": "css:main",
            "delay_before_return_html": 2.0,
        }

    def get_search_crawler_config(self) -> Dict[str, Any]:
        """
        Get portal-specific crawler configuration for search results pages.

        Returns:
            Dict with crawl4ai configuration parameters

        Default implementation:
            {
                "wait_for": "css:section",
                "delay_before_return_html": 3.0,
                "js_code": "window.scrollTo(0, document.body.scrollHeight);"
            }
        """
        return {
            "wait_for": "css:section",
            "delay_before_return_html": 3.0,
            "js_code": "window.scrollTo(0, document.body.scrollHeight);",
        }

    def preprocess_html(self, html: str) -> str:
        """
        Preprocess HTML to remove sections that cause false positive extractions.

        Default implementation returns HTML unchanged. Override in portal-specific
        adapters to remove problematic sections (e.g., mortgage calculators,
        affordability tools, comparison widgets).

        Args:
            html: Raw HTML content

        Returns:
            Cleaned HTML (default: unchanged)
        """
        return html
