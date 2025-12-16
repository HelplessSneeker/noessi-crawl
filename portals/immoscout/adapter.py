"""ImmobilienScout24.at portal adapter (BEST EFFORT IMPLEMENTATION)."""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from portals.base import PortalAdapter

logger = logging.getLogger(__name__)


class ImmoscoutAdapter(PortalAdapter):
    """
    Adapter for ImmobilienScout24.at (BEST EFFORT - needs validation).

    This implementation uses educated guesses based on common Austrian real estate
    site patterns. URL structure and extraction patterns may need refinement based
    on actual site structure.

    Implementation Strategy:
    - Multi-strategy extraction (JSON-LD → CSS selectors → Regex)
    - Comprehensive logging for debugging
    - Graceful fallbacks if patterns don't match

    IMPORTANT: First run will likely need refinement. User should test with
    max_pages=1 and provide logs/HTML samples for iteration.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Immoscout adapter with educated guess patterns."""
        super().__init__(config)
        self.postal_codes = config.get("postal_codes", [])
        logger.info(
            "ImmoscoutAdapter initialized (BEST EFFORT implementation). "
            f"Postal codes: {self.postal_codes}. "
            "First run may need refinement based on actual site structure."
        )

    def get_portal_name(self) -> str:
        """Return portal identifier."""
        return "immoscout"

    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize config (minimal changes for Immoscout).

        Unlike Willhaben, we assume postal codes can be used directly
        without translation to area IDs. If this assumption is wrong,
        will be revealed during testing.
        """
        normalized = config.copy()

        # Ensure postal_codes is a list
        if "postal_codes" in normalized and not isinstance(normalized["postal_codes"], list):
            normalized["postal_codes"] = [normalized["postal_codes"]]

        return normalized

    def build_search_url(self, page: int = 1, **kwargs) -> str:
        """
        Build search URL (VALIDATED structure from actual site).

        URL patterns:
        - Single postal code: /regional/1020/wohnung-kaufen?primaryPriceTo=150000
        - Multiple postal codes: /regional/wohnung-kaufen?countryCode=AT&zipCode=1030,1020&primaryPriceTo=150000
        - Pagination: &pageNumber=2 (assumed, may need verification)
        """
        base_url = "https://www.immobilienscout24.at/regional"

        # Check if we have single or multiple postal codes
        if self.postal_codes and len(self.postal_codes) == 1:
            # Single postal code: in path
            postal_code = self.postal_codes[0]
            url = f"{base_url}/{postal_code}/wohnung-kaufen"
            params = []
        elif self.postal_codes and len(self.postal_codes) > 1:
            # Multiple postal codes: in query parameter
            url = f"{base_url}/wohnung-kaufen"
            params = [
                "countryCode=AT",
                f"zipCode={','.join(str(code) for code in self.postal_codes)}"
            ]
            logger.debug(f"Multiple postal codes: {','.join(str(code) for code in self.postal_codes)}")
        else:
            # No postal codes specified
            url = f"{base_url}/wohnung-kaufen"
            params = ["countryCode=AT"]
            logger.warning("No postal codes specified - searching all of Austria")

        # Price filter (actual parameter name from site)
        max_price = self.filters.get("max_price")
        if max_price:
            params.append(f"primaryPriceTo={int(max_price)}")
            logger.debug(f"Price filter: primaryPriceTo={int(max_price)}")

        # Size filter (educated guess based on pattern - may need verification)
        min_size = self.filters.get("min_size_sqm")
        if min_size:
            params.append(f"primaryAreaFrom={int(min_size)}")

        max_size = self.filters.get("max_size_sqm")
        if max_size:
            params.append(f"primaryAreaTo={int(max_size)}")

        # Pagination (educated guess - may need verification)
        if page > 1:
            params.append(f"pageNumber={page}")

        # Build final URL
        if params:
            url = f"{url}?{'&'.join(params)}"

        logger.info(f"Generated Immoscout search URL (page {page}): {url}")
        return url

    def extract_listing_urls(self, html: str) -> List[Dict[str, str]]:
        """
        Extract listing URLs (MULTI-STRATEGY).

        Tries three strategies in order:
        1. JSON-LD structured data (preferred)
        2. CSS selector patterns (common real estate site patterns)
        3. Regex URL matching (last resort)

        Logs which strategy succeeded for debugging.
        """
        # Strategy 1: JSON-LD ItemList
        listings = self._extract_via_json_ld(html)
        if listings:
            logger.info(f"✅ Extracted {len(listings)} listings via JSON-LD (Strategy 1)")
            return listings

        # Strategy 2: CSS-like pattern matching (simplified, no actual CSS parsing)
        listings = self._extract_via_patterns(html)
        if listings:
            logger.info(f"✅ Extracted {len(listings)} listings via pattern matching (Strategy 2)")
            return listings

        # Strategy 3: Regex URL extraction
        listings = self._extract_via_regex(html)
        if listings:
            logger.info(f"✅ Extracted {len(listings)} listings via regex (Strategy 3)")
            return listings

        logger.warning(
            "⚠️  Failed to extract any listings. "
            "URL structure may be incorrect, or site may use AJAX loading. "
            "Please check browser network tab for actual search request."
        )
        return []

    def _extract_via_json_ld(self, html: str) -> List[Dict[str, str]]:
        """Extract listings from JSON-LD structured data."""
        try:
            # Find all JSON-LD scripts
            json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

            for json_text in json_ld_matches:
                try:
                    data = json.loads(json_text)

                    # Check for ItemList (common for search results)
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                        urls = []
                        for item in items:
                            url = None
                            # Try different JSON-LD structures
                            if isinstance(item, dict):
                                url = item.get("url") or item.get("item", {}).get("url")

                            if url:
                                # Make absolute URL if needed
                                if url.startswith("/"):
                                    url = f"https://www.immobilienscout24.at{url}"
                                urls.append({"url": url})

                        if urls:
                            logger.debug(f"Found {len(urls)} URLs in JSON-LD ItemList")
                            return urls

                    # Check for array of RealEstateListing
                    if isinstance(data, list):
                        urls = []
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") in ["RealEstateListing", "Product"]:
                                url = item.get("url")
                                if url:
                                    if url.startswith("/"):
                                        url = f"https://www.immobilienscout24.at{url}"
                                    urls.append({"url": url})
                        if urls:
                            logger.debug(f"Found {len(urls)} URLs in JSON-LD array")
                            return urls

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")

        return []

    def _extract_via_patterns(self, html: str) -> List[Dict[str, str]]:
        """Extract listings using common HTML patterns."""
        urls = []

        # Common patterns for real estate listing links
        # Try multiple patterns that are commonly used on Austrian real estate sites
        patterns = [
            r'<a[^>]+href=["\']([^"\']*(?:/expose/|/detail/|/immobilie/)[^"\']+)["\']',
            r'<a[^>]+href=["\']([^"\']*immobilienscout24\.at/[^"\']*expose[^"\']+)["\']',
            r'data-property-url=["\']([^"\']+)["\']',
            r'href=["\']([^"\']*wohnung[^"\']*kaufen[^"\']*\d{5,}[^"\']*)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                url = match
                # Make absolute URL
                if url.startswith("/"):
                    url = f"https://www.immobilienscout24.at{url}"
                # Filter out non-listing URLs
                if any(keyword in url.lower() for keyword in ["/expose/", "/detail/", "/immobilie/"]):
                    if url not in [u["url"] for u in urls]:  # Avoid duplicates
                        urls.append({"url": url})

        if urls:
            logger.debug(f"Pattern matching found {len(urls)} potential listing URLs")
        return urls

    def _extract_via_regex(self, html: str) -> List[Dict[str, str]]:
        """Extract listings using aggressive regex (last resort)."""
        # Look for URLs that contain listing ID patterns
        pattern = r'https?://(?:www\.)?immobilienscout24\.at/[^"\'<>\s]+?/(?:expose|detail|immobilie)/(\d{5,})'
        matches = re.findall(pattern, html, re.IGNORECASE)

        urls = []
        seen = set()
        for listing_id in matches:
            url = f"https://www.immobilienscout24.at/expose/{listing_id}"
            if url not in seen:
                urls.append({"url": url})
                seen.add(url)

        if urls:
            logger.debug(f"Regex extraction found {len(urls)} potential listing URLs")
        return urls

    def extract_listing_id(self, url: str) -> str:
        """
        Extract listing ID (PATTERN MATCHING).

        Expected patterns:
        - /expose/12345678 → 12345678
        - /detail/12345678 → 12345678
        - /immobilie/12345678 → 12345678

        Fallback: Hash of URL if pattern doesn't match
        """
        # Try multiple common patterns
        patterns = [
            r'/expose/(\d+)',
            r'/detail/(\d+)',
            r'/immobilie/(\d+)',
            r'/objekt/(\d+)',
            r'[/-](\d{5,})(?:[/?#]|$)',  # Generic: any 5+ digit number near end of path
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                listing_id = match.group(1)
                logger.debug(f"Extracted listing ID: {listing_id} from {url}")
                return listing_id

        # Fallback: use hash
        listing_id = str(abs(hash(url)))
        logger.warning(
            f"Could not extract listing ID from {url} using known patterns. "
            f"Using hash fallback: {listing_id}"
        )
        return listing_id

    def should_filter_ad(self, html: str) -> bool:
        """
        Check if listing is sponsored/premium ad (PATTERN-BASED).

        Common indicators on Austrian real estate sites:
        - CSS classes: premium, sponsored, featured, highlighted
        - Data attributes: data-premium="true", data-sponsored
        - Badge text: Top-Angebot, Premium, Highlight
        - Premium icons/badges

        Returns False if uncertain (keep listing by default).
        """
        # Check for common sponsored/premium indicators
        sponsored_patterns = [
            r'class=["\'][^"\']*(?:premium|sponsored|featured|highlight)[^"\']*["\']',
            r'data-premium=["\']true["\']',
            r'data-sponsored=["\']true["\']',
            r'data-ad-type=["\'](?:premium|sponsored)["\']',
            r'<[^>]*class=["\'][^"\']*badge[^"\']*["\'][^>]*>(?:Premium|Top|Highlight)',
        ]

        for pattern in sponsored_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                logger.debug("Filtering ad: Found sponsored/premium indicator")
                return True

        # If no indicators found, keep the listing
        return False

    def extract_address_from_html(self, html: str, url: str) -> Optional[str]:
        """
        Extract address (MULTI-SOURCE).

        Tries multiple extraction strategies:
        1. JSON-LD RealEstateListing address
        2. JSON-LD Product with location
        3. Common HTML patterns (address elements, meta tags)
        4. URL parsing (if address in path)

        Returns None if address cannot be extracted.
        """
        # Strategy 1: JSON-LD RealEstateListing
        address = self._extract_address_from_json_ld(html)
        if address:
            logger.debug(f"Extracted address from JSON-LD: {address}")
            return address

        # Strategy 2: HTML patterns
        address = self._extract_address_from_html_patterns(html)
        if address:
            logger.debug(f"Extracted address from HTML patterns: {address}")
            return address

        # Strategy 3: URL parsing (some sites include location in URL)
        address = self._extract_address_from_url(url)
        if address:
            logger.debug(f"Extracted address from URL: {address}")
            return address

        logger.debug(f"Could not extract address from {url}")
        return None

    def _extract_address_from_json_ld(self, html: str) -> Optional[str]:
        """Extract address from JSON-LD structured data."""
        try:
            json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

            for json_text in json_ld_matches:
                try:
                    data = json.loads(json_text)

                    # Check for RealEstateListing or Product
                    if isinstance(data, dict):
                        address_data = None

                        if data.get("@type") in ["RealEstateListing", "Product", "Offer"]:
                            # Try different address field names
                            address_data = (
                                data.get("address") or
                                data.get("location", {}).get("address") or
                                data.get("contentLocation", {}).get("address")
                            )

                        if address_data:
                            # Format address from structured data
                            if isinstance(address_data, dict):
                                parts = []
                                if address_data.get("streetAddress"):
                                    parts.append(address_data["streetAddress"])
                                if address_data.get("postalCode"):
                                    parts.append(address_data["postalCode"])
                                if address_data.get("addressLocality"):
                                    parts.append(address_data["addressLocality"])
                                if parts:
                                    return ", ".join(parts)
                            elif isinstance(address_data, str):
                                return address_data

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.debug(f"JSON-LD address extraction failed: {e}")

        return None

    def _extract_address_from_html_patterns(self, html: str) -> Optional[str]:
        """Extract address using common HTML patterns."""
        # Common address element patterns
        patterns = [
            r'<[^>]*class=["\'][^"\']*(?:property-address|object-location|address)[^"\']*["\'][^>]*>([^<]+)</[^>]*>',
            r'<[^>]*itemprop=["\']address["\'][^>]*>([^<]+)</[^>]*>',
            r'<address[^>]*>([^<]+)</address>',
            r'<h[12][^>]*class=["\'][^"\']*address[^"\']*["\'][^>]*>([^<]+)</h[12]>',
            r'data-address=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                # Clean up HTML entities and extra whitespace
                address = re.sub(r'\s+', ' ', address)
                if len(address) > 5:  # Sanity check
                    return address

        return None

    def _extract_address_from_url(self, url: str) -> Optional[str]:
        """Extract location information from URL path."""
        # Some sites include location like: /wien-1030-landstrasse/
        # Match city-postcode-district patterns before other URL segments
        # Pattern should match: /wien-1030-landstrasse/ but not /expose/ or /detail/
        pattern = r'/([a-z]+-\d{4}(?:-[a-z]+)?)'
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            location = match.group(1)
            # Convert hyphens to spaces and title case
            location = location.replace('-', ' ').title()
            if len(location) > 3:  # Sanity check
                return location

        return None

    def get_crawler_config(self) -> Dict[str, Any]:
        """
        Get crawler configuration for detail pages (EDUCATED GUESS).

        Assumes:
        - Content may load via JavaScript
        - Need to wait for main content container
        - 2 second delay should be sufficient for most AJAX

        May need adjustment based on actual site behavior.
        """
        return {
            "wait_for": "css:body",  # Generic wait - adjust if specific selector needed
            "delay_before_return_html": 2000,  # 2 seconds for AJAX
            "timeout": 30000,  # 30 seconds total timeout
        }

    def get_search_crawler_config(self) -> Dict[str, Any]:
        """
        Get crawler configuration for search results pages (EDUCATED GUESS).

        Similar to detail pages but may need different selectors.
        """
        return {
            "wait_for": "css:body",  # Adjust if results have specific container
            "delay_before_return_html": 2000,
            "timeout": 30000,
        }
