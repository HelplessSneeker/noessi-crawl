"""Austrian real estate extraction patterns and utilities."""

import logging
import re
from typing import Any, Dict, List, Optional, Pattern

from models.constants import VIENNA_DISTRICTS

logger = logging.getLogger(__name__)


class AustrianRealEstateExtractor:
    """Extractor for Austrian real estate listings using regex patterns."""

    # Size patterns (German) - updated to capture ranges, reject leading zeros
    SIZE_PATTERNS: List[Pattern] = [
        # First priority: ranges with m² (captures full range including dash/bis/to/~)
        re.compile(r"(?<![0-9.,])(\d+(?:[.,]\d+)?[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE),

        # Second priority: 2+ digits starting with 1-9 followed by m²
        re.compile(r"(?<![0-9.,])([1-9]\d+(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE),

        # Labeled patterns with word boundaries (capture ranges in labels)
        re.compile(r"\bWohnfläche[:\s]*(\d+(?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)", re.IGNORECASE),
        re.compile(r"\bNutzfläche[:\s]*(\d+(?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)", re.IGNORECASE),
        re.compile(r"\bFläche[:\s]*(\d+(?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)", re.IGNORECASE),

        # Fallback: any number with 2+ digits and m²
        re.compile(r"(?<![0-9.,])(\d{2,}(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE),
    ]

    # Room patterns - updated to capture ranges, require 1-9 start
    ROOM_PATTERNS: List[Pattern] = [
        # Require 1-9 digit start, capture ranges with dash/bis/to/~
        re.compile(r"([1-9](?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)\s*Zimmer", re.IGNORECASE),
        re.compile(r"([1-9](?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)\s*Zi\.?", re.IGNORECASE),
        re.compile(r"([1-9](?:[.,]\d+)?(?:[\s-]+(?:bis|to|~)?[\s-]*\d+(?:[.,]\d+)?)?)\s*Räume", re.IGNORECASE),
    ]

    # Price patterns - updated to capture ranges
    PRICE_PATTERNS: List[Pattern] = [
        re.compile(r"€\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)\s*€", re.IGNORECASE),
        re.compile(r"EUR\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)\s*EUR", re.IGNORECASE),
        re.compile(r"Kaufpreis[:\s]*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
    ]

    # Operating costs (Betriebskosten / Nebenkosten) - updated to capture ranges
    # Note: willhaben.at uses "Nebenkosten" instead of "Betriebskosten"
    BETRIEBSKOSTEN_PATTERNS: List[Pattern] = [
        # Inline patterns (label adjacent to value)
        re.compile(r"Betriebskosten[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"Nebenkosten[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"BK[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"NK[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"monatl\.?\s*(?:Betriebs|Neben)kosten[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),

        # Separated DOM patterns (label and value in different elements)
        re.compile(r"(?:Betriebs|Neben)kosten.*?€\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE | re.DOTALL),
        re.compile(r"(?:BK|NK).*?€\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE | re.DOTALL),

        # Table cell patterns (common in real estate listings)
        re.compile(r"<td[^>]*>(?:Betriebs|Neben)kosten</td>\s*<td[^>]*>€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r">(?:Betriebs|Neben)kosten<.*?>€\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)<", re.IGNORECASE | re.DOTALL),
    ]

    # Reparaturrücklage (repair fund) - updated to capture ranges
    REPARATUR_PATTERNS: List[Pattern] = [
        re.compile(r"Reparaturrücklage[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"Rep\.?\s*Rücklage[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
        re.compile(r"Rücklage[:\s]*€?\s*([\d.,\s-]+(?:bis|to|~)?[\d.,\s]*)", re.IGNORECASE),
    ]

    # Floor patterns
    FLOOR_PATTERNS: List[Pattern] = [
        re.compile(r"(\d+)\.\s*(?:Stock|OG|Obergeschoss)", re.IGNORECASE),
        re.compile(r"(?:Stock|Etage)[:\s]*(\d+)", re.IGNORECASE),
        re.compile(r"(\d+)\.\s*Etage", re.IGNORECASE),
        re.compile(r"(?:im\s+)?(\d+)\.\s*(?:Stock|OG)", re.IGNORECASE),
    ]

    # Special floor terms
    FLOOR_SPECIAL: Dict[str, int] = {
        "eg": 0,
        "erdgeschoss": 0,
        "erdgeschoß": 0,
        "parterre": 0,
        "hochparterre": 0,
        "hp": 0,
        "souterrain": -1,
        "keller": -1,
        "kellergeschoss": -1,
        "ug": -1,
        "untergeschoss": -1,
        "mezzanin": 1,
    }

    # Year built patterns
    YEAR_PATTERNS: List[Pattern] = [
        re.compile(r"Baujahr[:\s]*(\d{4})", re.IGNORECASE),
        re.compile(
            r"(?:erbaut|gebaut)[:\s]*(?:im\s+)?(?:Jahr\s+)?(\d{4})", re.IGNORECASE
        ),
        re.compile(r"aus\s+(?:dem\s+Jahr\s+)?(\d{4})", re.IGNORECASE),
    ]

    # Condition patterns
    CONDITION_PATTERNS: Dict[str, Pattern] = {
        "erstbezug": re.compile(r"Erstbezug(?!\s+nach)", re.IGNORECASE),
        "erstbezug_nach_sanierung": re.compile(
            r"Erstbezug\s+nach\s+(?:Sanierung|Renovierung)", re.IGNORECASE
        ),
        "saniert": re.compile(r"(?:frisch\s+)?(?:saniert|renoviert)", re.IGNORECASE),
        "renovierungsbedurftig": re.compile(
            r"(?:renovierung|sanierung)s?bedürftig", re.IGNORECASE
        ),
        "neuwertig": re.compile(r"neuwertig", re.IGNORECASE),
        "sehr_gut": re.compile(r"sehr\s+gut(?:er)?\s+(?:Zustand)?", re.IGNORECASE),
        "gut": re.compile(r"gut(?:er)?\s+Zustand", re.IGNORECASE),
        "gepflegt": re.compile(r"gepflegt", re.IGNORECASE),
    }

    # Building type patterns
    BUILDING_TYPE_PATTERNS: Dict[str, Pattern] = {
        "altbau": re.compile(r"Altbau", re.IGNORECASE),
        "neubau": re.compile(r"Neubau", re.IGNORECASE),
        "grunderzeit": re.compile(r"Gründerzeit", re.IGNORECASE),
    }

    # Energy rating patterns
    ENERGY_PATTERNS: List[Pattern] = [
        re.compile(r"Energieklasse[:\s]*([A-G]\+?\+?)", re.IGNORECASE),
        re.compile(r"HWB[:\s]*([\d.,]+)\s*kWh", re.IGNORECASE),
        re.compile(r"Heizwärmebedarf[:\s]*([\d.,]+)", re.IGNORECASE),
        re.compile(r"fGEE[:\s]*([\d.,]+)", re.IGNORECASE),
    ]

    # Heating type patterns
    HEATING_PATTERNS: Dict[str, Pattern] = {
        "fernwarme": re.compile(r"Fernwärme", re.IGNORECASE),
        "gas": re.compile(r"Gas(?:heizung|therme)?", re.IGNORECASE),
        "zentralheizung": re.compile(r"Zentralheizung", re.IGNORECASE),
        "etagenheizung": re.compile(r"Etagenheizung", re.IGNORECASE),
        "fussbodenheizung": re.compile(r"Fußbodenheizung", re.IGNORECASE),
        "elektro": re.compile(r"Elektro(?:heizung)?", re.IGNORECASE),
        "warmepumpe": re.compile(r"Wärmepumpe", re.IGNORECASE),
    }

    # Feature patterns (boolean)
    FEATURE_PATTERNS: Dict[str, Pattern] = {
        "elevator": re.compile(r"(?:Aufzug|Lift|Fahrstuhl)", re.IGNORECASE),
        "balcony": re.compile(r"Balkon", re.IGNORECASE),
        "terrace": re.compile(r"Terrasse", re.IGNORECASE),
        "loggia": re.compile(r"Loggia", re.IGNORECASE),
        "garden": re.compile(r"Garten(?!straße)", re.IGNORECASE),
        "cellar": re.compile(r"Keller(?:abteil)?", re.IGNORECASE),
        "storage": re.compile(r"(?:Abstell|Lager)raum", re.IGNORECASE),
        "parking": re.compile(
            r"(?:Garage|Tiefgarage|Stellplatz|Parkplatz|Carport)", re.IGNORECASE
        ),
        "furnished": re.compile(r"(?:möbliert|eingerichtet)", re.IGNORECASE),
        "barrier_free": re.compile(r"barrierefrei", re.IGNORECASE),
    }

    # Parking type extraction
    PARKING_TYPE_PATTERNS: Dict[str, Pattern] = {
        "tiefgarage": re.compile(r"Tiefgarage", re.IGNORECASE),
        "garage": re.compile(r"(?<!Tief)Garage", re.IGNORECASE),
        "stellplatz": re.compile(r"Stellplatz", re.IGNORECASE),
        "carport": re.compile(r"Carport", re.IGNORECASE),
        "parkplatz": re.compile(r"Parkplatz", re.IGNORECASE),
    }

    # Commission patterns
    COMMISSION_PATTERNS: List[Pattern] = [
        re.compile(r"provision(?:s)?frei", re.IGNORECASE),
        re.compile(r"keine\s+(?:Makler)?provision", re.IGNORECASE),
        re.compile(r"(?:Makler)?provision[:\s]*([\d.,]+)\s*%", re.IGNORECASE),
    ]

    def __init__(self):
        """Initialize the extractor."""
        pass

    def extract_field(
        self,
        text: str,
        patterns: List[Pattern],
        group: int = 1,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        parse_ranges: bool = True,
    ) -> Optional[str]:
        """
        Extract first matching value from text using patterns.

        Args:
            text: HTML text to search
            patterns: List of regex patterns to try
            group: Regex group number to extract (default: 1)
            min_value: Minimum acceptable numeric value (filters out placeholders)
            max_value: Maximum acceptable numeric value (sanity check)
            parse_ranges: If True, detect ranges and extract lower value (default: True)

        Returns:
            Matched string value, or None if no valid match found
        """
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value_str = match.group(group)

                # If validation requested, check numeric bounds
                if min_value is not None or max_value is not None:
                    # Use range-aware parsing if requested
                    parsed = self.parse_number_with_range(value_str) if parse_ranges else self.parse_number(value_str)
                    if parsed is not None:
                        if min_value is not None and parsed < min_value:
                            # Skip this match - too low (likely placeholder)
                            logger.debug(
                                f"Rejected value {parsed} (< min {min_value}) from '{value_str}'"
                            )
                            continue
                        if max_value is not None and parsed > max_value:
                            # Skip this match - too high (likely error)
                            logger.debug(
                                f"Rejected value {parsed} (> max {max_value}) from '{value_str}'"
                            )
                            continue

                return value_str
        return None

    def extract_boolean(self, text: str, pattern: Pattern) -> bool:
        """Check if pattern exists in text."""
        return bool(pattern.search(text))

    def parse_number(self, value: str) -> Optional[float]:
        """Parse German-formatted number to float.

        Handles German number format where:
        - Dot (.) is thousands separator
        - Comma (,) is decimal separator

        Examples:
            "100.000" → 100000.0
            "2,5" → 2.5
            "100.000,50" → 100000.5
        """
        if not value:
            return None
        # Handle German number format:
        # 1. Remove spaces
        # 2. Replace comma (decimal separator) with placeholder
        # 3. Remove all dots (thousands separators)
        # 4. Replace placeholder with dot
        cleaned = value.strip().replace(" ", "").replace(",", "###DECIMAL###").replace(".", "").replace("###DECIMAL###", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def parse_number_with_range(self, value: str) -> Optional[float]:
        """
        Parse German-formatted number, handling ranges by returning lower value.

        Detects patterns:
        - "40-140" or "40 - 140"
        - "40 bis 140"
        - "40~140" or "40 ~ 140"
        - "40 to 140"

        Returns the LOWER value (conservative approach for investment analysis).

        Args:
            value: String potentially containing a number or range

        Returns:
            Float value (lower bound if range detected), or None if unparseable

        Examples:
            "40-140 m²" → 40.0
            "100.000-150.000" → 100000.0
            "2,5 bis 3,5" → 2.5
            "50" → 50.0
        """
        if not value:
            return None

        # Clean the string
        cleaned = value.strip()

        # Range separators (in order of specificity)
        range_patterns = [
            r'(\d+[.,\s]*\d*)\s*-\s*(\d+[.,\s]*\d*)',      # "40-140" or "40 - 140"
            r'(\d+[.,\s]*\d*)\s+bis\s+(\d+[.,\s]*\d*)',    # "40 bis 140"
            r'(\d+[.,\s]*\d*)\s*~\s*(\d+[.,\s]*\d*)',      # "40~140"
            r'(\d+[.,\s]*\d*)\s+to\s+(\d+[.,\s]*\d*)',     # "40 to 140"
        ]

        for pattern in range_patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                lower_str = match.group(1)
                upper_str = match.group(2)

                # Parse both bounds
                lower = self.parse_number(lower_str)
                upper = self.parse_number(upper_str)

                if lower is not None and upper is not None:
                    # Validate: lower should be less than upper
                    if lower < upper:
                        logger.debug(
                            f"Range detected: '{value}' → using lower bound {lower} "
                            f"(upper: {upper})"
                        )
                        return lower
                    else:
                        logger.warning(
                            f"Invalid range detected (lower >= upper): '{value}' "
                            f"(lower: {lower}, upper: {upper}), using lower value"
                        )
                        # For invalid range, still return the lower value (first number)
                        return lower

        # No range detected - parse as single number
        return self.parse_number(value)

    def parse_district_from_postal(self, postal_code: str) -> Optional[int]:
        """
        Extract Vienna district number from postal code.

        Vienna postal codes: 1XXX where XX is the district (01-23).
        Example: 1030 -> district 3, 1220 -> district 22
        """
        if not postal_code or not postal_code.startswith("1"):
            return None

        try:
            code = int(postal_code)
            if 1010 <= code <= 1239:
                # Extract district: 1030 -> 03 -> 3
                district = (code % 1000) // 10
                if 1 <= district <= 23:
                    return district
        except ValueError:
            pass
        return None

    def extract_floor(self, text: str) -> Dict[str, Any]:
        """Extract floor information from text."""
        result = {"floor": None, "floor_text": None}

        # Check special floor terms first
        text_lower = text.lower()
        for term, floor_num in self.FLOOR_SPECIAL.items():
            if term in text_lower:
                result["floor"] = floor_num
                result["floor_text"] = (
                    term.upper() if term in ["eg", "dg", "ug", "hp"] else term.title()
                )
                return result

        # Check for Dachgeschoss
        if re.search(r"(?:DG|Dachgeschoss|Dachgeschoß)", text, re.IGNORECASE):
            result["floor_text"] = "DG"
            return result

        # Try numeric patterns
        for pattern in self.FLOOR_PATTERNS:
            match = pattern.search(text)
            if match:
                result["floor"] = int(match.group(1))
                result["floor_text"] = f"{result['floor']}. OG"
                return result

        return result

    def extract_from_html_dom(self, html: str) -> Dict[str, Any]:
        """
        Extract fields using HTML DOM parsing (more reliable for separated labels/values).

        Falls back gracefully if BeautifulSoup is not available.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping DOM extraction")
            return {}

        try:
            soup = BeautifulSoup(html, 'html.parser')
            extracted: Dict[str, Any] = {}

            # Find betriebskosten/nebenkosten in table rows or definition lists
            # Pattern 1: Table rows with label/value cells
            for row in soup.find_all(['tr', 'div', 'dl']):
                cells = row.find_all(['td', 'div', 'span', 'dd', 'dt'])
                if len(cells) >= 2:
                    # Check each pair of cells
                    for i in range(len(cells) - 1):
                        label_text = cells[i].get_text(strip=True).lower()
                        value_text = cells[i + 1].get_text(strip=True)

                        # Look for betriebskosten/nebenkosten keywords
                        if any(keyword in label_text for keyword in ['betriebskosten', 'nebenkosten', 'bk', 'nk']):
                            # Extract numeric value (allow dash for ranges)
                            value_match = re.search(r'([\d.,\s-]+)', value_text)
                            if value_match:
                                bk_value = self.parse_number_with_range(value_match.group(1))
                                # Validate range (reject placeholders)
                                if bk_value and 20 <= bk_value < 2000:
                                    extracted["betriebskosten_monthly"] = bk_value
                                    logger.debug(f"DOM extracted betriebskosten: €{bk_value} from '{label_text}' / '{value_text}'")
                                    break

                if "betriebskosten_monthly" in extracted:
                    break

            # Pattern 2: Look for specific willhaben.at structure
            # (Can be extended based on actual HTML structure)

            return extracted

        except Exception as e:
            logger.debug(f"DOM extraction failed: {e}")
            return {}

    def extract_from_html(self, html: str) -> Dict[str, Any]:
        """
        Extract all available fields from HTML content.

        Returns a dictionary of extracted values.
        """
        extracted: Dict[str, Any] = {}

        # Size - with range parsing and validation (10-500 m²)
        size_str = self.extract_field(
            html,
            self.SIZE_PATTERNS,
            parse_ranges=True,
            min_value=10.0,   # Reject < 10 m² (extraction errors)
            max_value=500.0   # Sanity check: reject mansions/commercial
        )
        if size_str:
            extracted["size_sqm"] = self.parse_number_with_range(size_str)

        # Rooms - with range parsing
        rooms_str = self.extract_field(html, self.ROOM_PATTERNS, parse_ranges=True)
        if rooms_str:
            extracted["rooms"] = self.parse_number_with_range(rooms_str)

        # Price - with range parsing
        price_str = self.extract_field(html, self.PRICE_PATTERNS, parse_ranges=True)
        if price_str:
            extracted["price"] = self.parse_number_with_range(price_str)

        # Betriebskosten / Nebenkosten - with range parsing
        # Use min_value to reject placeholder values like "€1"
        bk_str = self.extract_field(
            html,
            self.BETRIEBSKOSTEN_PATTERNS,
            min_value=10.0,  # Reject unrealistic values under €10/month
            max_value=2000.0,  # Sanity check: max €2000/month
            parse_ranges=True
        )
        if bk_str:
            extracted["betriebskosten_monthly"] = self.parse_number_with_range(bk_str)

        # Reparaturrücklage - with range parsing
        rep_str = self.extract_field(html, self.REPARATUR_PATTERNS, parse_ranges=True)
        if rep_str:
            extracted["reparaturrucklage"] = self.parse_number_with_range(rep_str)

        # Floor
        floor_info = self.extract_floor(html)
        if floor_info["floor"] is not None:
            extracted["floor"] = floor_info["floor"]
        if floor_info["floor_text"]:
            extracted["floor_text"] = floor_info["floor_text"]

        # Year built
        year_str = self.extract_field(html, self.YEAR_PATTERNS)
        if year_str:
            try:
                year = int(year_str)
                if 1800 <= year <= 2030:
                    extracted["year_built"] = year
            except ValueError:
                pass

        # Condition
        for condition_key, pattern in self.CONDITION_PATTERNS.items():
            if self.extract_boolean(html, pattern):
                extracted["condition"] = condition_key
                break

        # Building type
        for building_key, pattern in self.BUILDING_TYPE_PATTERNS.items():
            if self.extract_boolean(html, pattern):
                extracted["building_type"] = building_key
                break

        # Energy rating
        energy_class = self.extract_field(html, self.ENERGY_PATTERNS[:1])
        if energy_class:
            extracted["energy_rating"] = energy_class.upper()

        # HWB value
        hwb_str = self.extract_field(html, self.ENERGY_PATTERNS[1:2])
        if hwb_str:
            extracted["hwb_value"] = self.parse_number(hwb_str)

        # fGEE value
        fgee_str = self.extract_field(html, self.ENERGY_PATTERNS[3:4])
        if fgee_str:
            extracted["fgee_value"] = self.parse_number(fgee_str)

        # Heating type
        for heating_key, pattern in self.HEATING_PATTERNS.items():
            if self.extract_boolean(html, pattern):
                extracted["heating_type"] = heating_key
                break

        # Boolean features
        for feature_key, pattern in self.FEATURE_PATTERNS.items():
            if self.extract_boolean(html, pattern):
                extracted[feature_key] = True

        # Parking type (more specific than boolean)
        for parking_key, pattern in self.PARKING_TYPE_PATTERNS.items():
            if self.extract_boolean(html, pattern):
                extracted["parking"] = parking_key
                break

        # Commission
        if re.search(
            r"provision(?:s)?frei|keine\s+(?:Makler)?provision", html, re.IGNORECASE
        ):
            extracted["commission_free"] = True
        else:
            commission_match = re.search(
                r"(?:Makler)?provision[:\s]*([\d.,]+)\s*%", html, re.IGNORECASE
            )
            if commission_match:
                extracted["commission_free"] = False
                extracted["commission_percent"] = self.parse_number(
                    commission_match.group(1)
                )

        return extracted
