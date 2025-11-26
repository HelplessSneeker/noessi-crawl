"""Austrian address parsing utilities."""

import re
from typing import Any, Dict, Optional

from models.constants import AUSTRIAN_STATES, POSTAL_CODE_RANGES, VIENNA_DISTRICTS


class AustrianAddressParser:
    """Parser for Austrian address formats."""

    # Austrian address pattern
    # Examples:
    #   "Margaretenstraße 12/3/4, 1050 Wien"
    #   "Hauptplatz 1, 8010 Graz"
    #   "Rathausplatz 3 Top 5, 1010 Wien"
    ADDRESS_PATTERN = re.compile(
        r"""
        (?P<street>[A-Za-zäöüÄÖÜß\s\-\.]+?)  # Street name
        \s*
        (?P<house_number>\d+[a-zA-Z]?)        # House number (e.g., 12, 12a)
        (?:                                    # Optional door/top number
            \s*[/\-]\s*
            (?P<stair>\d+)?                   # Staircase number
            (?:\s*[/\-]\s*)?
            (?P<door>\d+|Top\s*\d+)?          # Door/Top number
        )?
        \s*[,\s]+\s*
        (?P<postal>\d{4})                     # Postal code (4 digits)
        \s+
        (?P<city>[A-Za-zäöüÄÖÜß\s\-]+)       # City name
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Simpler pattern for partial addresses
    POSTAL_CITY_PATTERN = re.compile(
        r"(?P<postal>\d{4})\s+(?P<city>[A-Za-zäöüÄÖÜß\s\-]+)"
    )

    # Pattern for city-only format (from URL extraction)
    CITY_ONLY_PATTERN = re.compile(
        r"^(?P<city>[A-Za-zäöüÄÖÜß\s\-]+?)(?:\s*,\s*(?P<state>[A-Za-zäöüÄÖÜß\s\-]+))?$"
    )

    # Vienna-specific street suffixes
    STREET_SUFFIXES = [
        "straße",
        "strasse",
        "gasse",
        "weg",
        "platz",
        "ring",
        "allee",
        "zeile",
        "promenade",
        "kai",
        "ufer",
    ]

    def __init__(self):
        """Initialize the parser."""
        pass

    def parse_address(self, address_text: str) -> Dict[str, Any]:
        """
        Parse an Austrian address string into components.

        Args:
            address_text: Raw address string

        Returns:
            Dictionary with parsed address components
        """
        result: Dict[str, Any] = {
            "street": None,
            "house_number": None,
            "door_number": None,
            "postal_code": None,
            "city": None,
            "district": None,
            "district_number": None,
            "state": None,
            "full_address": address_text.strip() if address_text else None,
        }

        if not address_text:
            return result

        # Try full address pattern
        match = self.ADDRESS_PATTERN.search(address_text)
        if match:
            result["street"] = match.group("street").strip()
            result["house_number"] = match.group("house_number")
            result["postal_code"] = match.group("postal")
            result["city"] = match.group("city").strip()

            # Build door number from stair/door
            stair = match.group("stair")
            door = match.group("door")
            if stair and door:
                result["door_number"] = f"{stair}/{door}"
            elif door:
                # Handle "Top X" format
                door_str = door.replace("Top", "").strip()
                result["door_number"] = door_str
            elif stair:
                result["door_number"] = stair
        else:
            # Try simpler postal/city pattern
            simple_match = self.POSTAL_CITY_PATTERN.search(address_text)
            if simple_match:
                result["postal_code"] = simple_match.group("postal")
                result["city"] = simple_match.group("city").strip()
            else:
                # Try city-only pattern (e.g., "Villach, Kaernten" or just "Villach")
                city_match = self.CITY_ONLY_PATTERN.match(address_text.strip())
                if city_match:
                    result["city"] = city_match.group("city").strip()
                    if city_match.group("state"):
                        result["state"] = city_match.group("state").strip()

        # Determine state and district from postal code
        if result["postal_code"]:
            result["state"] = self._get_state_from_postal(result["postal_code"])

            # Vienna district extraction
            if result["postal_code"].startswith("1"):
                district_num = self._parse_vienna_district(result["postal_code"])
                if district_num:
                    result["district_number"] = district_num
                    result["district"] = VIENNA_DISTRICTS.get(district_num, {}).get(
                        "name"
                    )
                    result["city"] = "Wien"

        return result

    def _parse_vienna_district(self, postal_code: str) -> Optional[int]:
        """
        Extract Vienna district number from postal code.

        Vienna postal codes: 1XXX where XX is the district (01-23).
        Example: 1030 -> district 3, 1220 -> district 22
        """
        try:
            code = int(postal_code)
            if 1010 <= code <= 1239:
                district = (code % 1000) // 10
                if 1 <= district <= 23:
                    return district
        except ValueError:
            pass
        return None

    def _get_state_from_postal(self, postal_code: str) -> Optional[str]:
        """Determine Austrian state from postal code."""
        try:
            code = int(postal_code)
            for state, (start, end) in POSTAL_CODE_RANGES.items():
                if start <= code <= end:
                    return state
        except ValueError:
            pass
        return None

    def format_address(
        self,
        street: Optional[str] = None,
        house_number: Optional[str] = None,
        door_number: Optional[str] = None,
        postal_code: Optional[str] = None,
        city: Optional[str] = None,
    ) -> str:
        """Format address components into a standard string."""
        parts = []

        if street:
            street_part = street
            if house_number:
                street_part += f" {house_number}"
            if door_number:
                street_part += f"/{door_number}"
            parts.append(street_part)

        if postal_code and city:
            parts.append(f"{postal_code} {city}")
        elif city:
            parts.append(city)

        return ", ".join(parts)

    def extract_district_from_text(self, text: str) -> Optional[int]:
        """
        Extract Vienna district number from text.

        Handles formats like:
        - "1030 Wien"
        - "Wien 3. Bezirk"
        - "3., Landstraße"
        - "Wien-Landstraße"
        """
        if not text:
            return None

        # Try postal code first
        postal_match = re.search(r"\b(1\d{3})\b", text)
        if postal_match:
            district = self._parse_vienna_district(postal_match.group(1))
            if district:
                return district

        # Try "X. Bezirk" pattern
        bezirk_match = re.search(r"(\d{1,2})\.\s*Bezirk", text, re.IGNORECASE)
        if bezirk_match:
            district = int(bezirk_match.group(1))
            if 1 <= district <= 23:
                return district

        # Try district name lookup
        text_lower = text.lower()
        for district_num, info in VIENNA_DISTRICTS.items():
            if info["name"].lower() in text_lower:
                return district_num

        return None
