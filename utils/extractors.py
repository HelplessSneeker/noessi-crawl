"""Austrian real estate extraction patterns and utilities."""

import re
from typing import Any, Dict, List, Optional, Pattern

from models.constants import VIENNA_DISTRICTS


class AustrianRealEstateExtractor:
    """Extractor for Austrian real estate listings using regex patterns."""

    # Size patterns (German)
    SIZE_PATTERNS: List[Pattern] = [
        re.compile(r"(\d+[.,]?\d*)\s*m[²2]", re.IGNORECASE),
        re.compile(r"Wohnfläche[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        re.compile(r"Nutzfläche[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
        re.compile(r"Fläche[:\s]*(\d+[.,]?\d*)", re.IGNORECASE),
    ]

    # Room patterns
    ROOM_PATTERNS: List[Pattern] = [
        re.compile(r"(\d+[.,]?\d*)\s*Zimmer", re.IGNORECASE),
        re.compile(r"(\d+[.,]?\d*)\s*Zi\.?", re.IGNORECASE),
        re.compile(r"(\d+[.,]?\d*)\s*Räume", re.IGNORECASE),
    ]

    # Price patterns
    PRICE_PATTERNS: List[Pattern] = [
        re.compile(r"€\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"([\d.,]+)\s*€", re.IGNORECASE),
        re.compile(r"EUR\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"([\d.,]+)\s*EUR", re.IGNORECASE),
        re.compile(r"Kaufpreis[:\s]*([\d.,]+)", re.IGNORECASE),
    ]

    # Operating costs (Betriebskosten)
    BETRIEBSKOSTEN_PATTERNS: List[Pattern] = [
        re.compile(r"Betriebskosten[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"BK[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"monatl\.?\s*Betriebskosten[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
    ]

    # Reparaturrücklage (repair fund)
    REPARATUR_PATTERNS: List[Pattern] = [
        re.compile(r"Reparaturrücklage[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"Rep\.?\s*Rücklage[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
        re.compile(r"Rücklage[:\s]*€?\s*([\d.,]+)", re.IGNORECASE),
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
        self, text: str, patterns: List[Pattern], group: int = 1
    ) -> Optional[str]:
        """Extract first matching value from text using patterns."""
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(group)
        return None

    def extract_boolean(self, text: str, pattern: Pattern) -> bool:
        """Check if pattern exists in text."""
        return bool(pattern.search(text))

    def parse_number(self, value: str) -> Optional[float]:
        """Parse German-formatted number to float."""
        if not value:
            return None
        # Remove spaces and handle German number format
        cleaned = value.strip().replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

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

    def extract_from_html(self, html: str) -> Dict[str, Any]:
        """
        Extract all available fields from HTML content.

        Returns a dictionary of extracted values.
        """
        extracted: Dict[str, Any] = {}

        # Size
        size_str = self.extract_field(html, self.SIZE_PATTERNS)
        if size_str:
            extracted["size_sqm"] = self.parse_number(size_str)

        # Rooms
        rooms_str = self.extract_field(html, self.ROOM_PATTERNS)
        if rooms_str:
            extracted["rooms"] = self.parse_number(rooms_str)

        # Price
        price_str = self.extract_field(html, self.PRICE_PATTERNS)
        if price_str:
            extracted["price"] = self.parse_number(price_str)

        # Betriebskosten
        bk_str = self.extract_field(html, self.BETRIEBSKOSTEN_PATTERNS)
        if bk_str:
            extracted["betriebskosten_monthly"] = self.parse_number(bk_str)

        # Reparaturrücklage
        rep_str = self.extract_field(html, self.REPARATUR_PATTERNS)
        if rep_str:
            extracted["reparaturrucklage"] = self.parse_number(rep_str)

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
