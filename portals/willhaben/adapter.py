"""Willhaben.at portal adapter."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from portals.base import PortalAdapter
from portals.willhaben.constants import PLZ_TO_AREA_ID

logger = logging.getLogger(__name__)


class WillhabenAdapter(PortalAdapter):
    """Adapter for Willhaben.at Austrian real estate portal."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Willhaben adapter.

        Translates postal_codes to Willhaben-specific area_ids.
        Supports both postal_codes (new format) and area_ids (legacy).
        """
        super().__init__(config)
        self.area_ids = self._translate_postal_codes_to_area_ids()

    def _translate_postal_codes_to_area_ids(self) -> List[int]:
        """Translate postal codes from config to willhaben area_ids."""
        area_ids = []

        # Support both old format (area_ids) and new format (postal_codes)
        if "postal_codes" in self.config:
            postal_codes = self.config["postal_codes"]
            for plz in postal_codes:
                plz_str = str(plz)
                if plz_str in PLZ_TO_AREA_ID:
                    area_ids.append(PLZ_TO_AREA_ID[plz_str])
                    logger.debug(
                        f"Translated PLZ {plz_str} to area_id {PLZ_TO_AREA_ID[plz_str]}"
                    )
                else:
                    logger.warning(
                        f"Unknown postal code {plz_str} - no area_id mapping found"
                    )
        elif "area_ids" in self.config:
            # Legacy support: use area_ids directly
            area_ids = self.config["area_ids"]
            logger.info("Using legacy 'area_ids' format from config")
        else:
            logger.warning("No 'postal_codes' or 'area_ids' found in config")

        return area_ids

    def get_portal_name(self) -> str:
        """Return portal identifier."""
        return "willhaben"

    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize config (Willhaben uses area_ids internally).

        Returns:
            Config with 'area_ids' field populated
        """
        normalized = config.copy()
        normalized["area_ids"] = self.area_ids
        return normalized

    def build_search_url(self, page: int = 1, **kwargs) -> str:
        """Build willhaben.at search URL from configuration parameters."""
        base_url = "https://www.willhaben.at/iad/immobilien/eigentumswohnung/eigentumswohnung-angebote"

        params = []

        # Add area IDs (translated from postal codes)
        for area_id in self.area_ids:
            params.append(f"areaId={area_id}")

        # Add price threshold from filters
        max_price = self.filters.get("max_price")
        if max_price:
            params.append(f"PRICE_TO={int(max_price)}")

        # Add pagination
        params.append(f"page={page}")
        params.append("isNavigation=true")

        return f"{base_url}?{'&'.join(params)}"

    def extract_listing_urls(self, html: str) -> List[Dict[str, str]]:
        """Extract apartment URLs from JSON-LD structured data."""
        try:
            match = re.search(
                r'<script type="application/ld\+json">({.*?"@type":"ItemList".*?})</script>',
                html,
                re.DOTALL,
            )
            if match:
                json_data = json.loads(match.group(1))
                items = json_data.get("itemListElement", [])
                return [
                    {"url": f"https://www.willhaben.at{item.get('url', '')}"}
                    for item in items
                    if item.get("url")
                ]
        except Exception as e:
            logger.warning(f"Error extracting JSON-LD: {e}")
        return []

    def extract_listing_id(self, url: str) -> str:
        """Extract listing ID from URL."""
        # willhaben URLs typically end with the listing ID
        match = re.search(r"/(\d+)/?$", url)
        if match:
            return match.group(1)
        # Fallback to hash of URL
        return str(hash(url))

    def should_filter_ad(self, html: str) -> bool:
        """
        Check if listing is a promoted ad.

        Willhaben uses star icon SVG path to indicate real listings.

        Returns:
            True if should filter (is an ad), False otherwise
        """
        star_icon_path = "m12 4 2.09 4.25a1.52 1.52 0 0 0 1.14.82l4.64.64-3.42 3.32"
        # Star icon present = real listing, absent = promoted ad
        return star_icon_path not in html

    def extract_address_from_html(self, html: str, url: str) -> Optional[str]:
        """
        Extract address from HTML or URL.

        Uses 3 strategies: JSON-LD, HTML patterns, URL patterns.
        """
        # Strategy 1: Look for address in JSON-LD
        json_ld_match = re.search(
            r'"address"[:\s]*\{[^}]*"streetAddress"[:\s]*"([^"]+)"', html
        )
        if json_ld_match:
            addr = json_ld_match.group(1).strip()
            # Only return if it looks like a real address (has street name or postal code)
            if re.search(r"\d{4}|straße|gasse|weg|platz", addr, re.IGNORECASE):
                return addr

        # Strategy 2: Look for address in structured data attributes
        # willhaben often has address in data attributes or specific divs
        address_patterns = [
            # Full address with street, postal code and city
            r"([A-Za-zäöüÄÖÜß\-]+(?:straße|gasse|weg|platz|ring|allee)\s+\d+[^,<]*,\s*\d{4}\s+[A-Za-zäöüÄÖÜß\s]+)",
            # Postal code + city pattern (more cities)
            r"(\d{4})\s+(Wien|Graz|Linz|Salzburg|Innsbruck|Klagenfurt|Villach|St\.\s*Pölten|Wels|Dornbirn|Steyr|Wiener\s*Neustadt|Feldkirch|Bregenz)[^<]*",
            # Address label patterns
            r"(?:Adresse|Standort|Lage)[:\s]*</[^>]+>\s*<[^>]+>([^<]+)",
            r"(?:Adresse|Standort|Lage)[:\s]*([^<\n]{10,80})",
        ]

        for pattern in address_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                addr = (
                    match.group(1).strip()
                    if match.lastindex
                    else match.group(0).strip()
                )
                # Clean up HTML entities and extra whitespace
                addr = re.sub(r"\s+", " ", addr)
                addr = addr.replace("&nbsp;", " ").strip()
                if len(addr) > 5 and len(addr) < 200:
                    return addr

        # Strategy 3: Extract from URL
        # Pattern: /wien-1030-landstrasse/ or /kaernten/klagenfurt/
        url_patterns = [
            # Vienna with postal code: /wien-1030-landstrasse/
            (
                r"/wien-(\d{4})-([^/]+)",
                lambda m: f"{m.group(1)} Wien",
            ),
            # Other cities with postal code: /1030-landstrasse/
            (
                r"/(\d{4})-([^/]+)",
                lambda m: f"{m.group(1)}",
            ),
            # State/City format: /kaernten/villach/ or /wien/leopoldstadt/
            (
                r"/(?:kaernten|kärnten)/([a-z\-]+)/",
                lambda m: f"{m.group(1).replace('-', ' ').title()}, Kärnten",
            ),
            (
                r"/(?:steiermark)/([a-z\-]+)/",
                lambda m: f"{m.group(1).replace('-', ' ').title()}, Steiermark",
            ),
            (
                r"/(?:tirol)/([a-z\-]+)/",
                lambda m: f"{m.group(1).replace('-', ' ').title()}, Tirol",
            ),
            (
                r"/wien/([a-z\-]+)/",
                lambda m: "Wien",
            ),
        ]

        for pattern, formatter in url_patterns:
            match = re.search(pattern, url.lower())
            if match:
                return formatter(match)

        return None
