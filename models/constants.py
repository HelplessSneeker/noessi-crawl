"""Austrian real estate constants and enums."""

from enum import Enum
from typing import Dict, List

# Property condition types (German)
CONDITION_TYPES: Dict[str, str] = {
    "erstbezug": "First occupancy",
    "erstbezug_nach_sanierung": "First occupancy after renovation",
    "saniert": "Renovated",
    "renovierungsbedurftig": "Needs renovation",
    "gut": "Good condition",
    "sehr_gut": "Very good condition",
    "neuwertig": "Like new",
    "gepflegt": "Well maintained",
}

# Building types
BUILDING_TYPES: Dict[str, str] = {
    "altbau": "Old building (pre-1945)",
    "neubau": "New building (post-1945)",
    "grunderzeit": "Gründerzeit (1848-1918)",
    "zwischenkrieg": "Interwar period (1918-1945)",
    "nachkrieg": "Post-war (1945-1970)",
    "modern": "Modern (post-1970)",
}

# Parking types
PARKING_TYPES: Dict[str, str] = {
    "tiefgarage": "Underground garage",
    "garage": "Garage",
    "stellplatz": "Parking space",
    "carport": "Carport",
    "parkplatz": "Parking lot",
    "ohne": "No parking",
}

# Heating types
HEATING_TYPES: Dict[str, str] = {
    "fernwarme": "District heating",
    "gas": "Gas heating",
    "zentralheizung": "Central heating",
    "etagenheizung": "Floor heating",
    "fussbodenheizung": "Underfloor heating",
    "elektro": "Electric heating",
    "ol": "Oil heating",
    "pellets": "Pellet heating",
    "warmepumpe": "Heat pump",
    "solar": "Solar heating",
}

# Energy efficiency ratings
ENERGY_RATINGS: List[str] = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]

# Energy rating thresholds (HWB kWh/m2a)
ENERGY_RATING_THRESHOLDS: Dict[str, tuple] = {
    "A++": (0, 10),
    "A+": (10, 15),
    "A": (15, 25),
    "B": (25, 50),
    "C": (50, 100),
    "D": (100, 150),
    "E": (150, 200),
    "F": (200, 250),
    "G": (250, float("inf")),
}

# Vienna districts with names and rent multipliers
# Multipliers are relative to base rent (1.0 = average)
VIENNA_DISTRICTS: Dict[int, Dict[str, any]] = {
    1: {"name": "Innere Stadt", "multiplier": 1.40},
    2: {"name": "Leopoldstadt", "multiplier": 1.10},
    3: {"name": "Landstraße", "multiplier": 1.15},
    4: {"name": "Wieden", "multiplier": 1.20},
    5: {"name": "Margareten", "multiplier": 1.05},
    6: {"name": "Mariahilf", "multiplier": 1.15},
    7: {"name": "Neubau", "multiplier": 1.20},
    8: {"name": "Josefstadt", "multiplier": 1.20},
    9: {"name": "Alsergrund", "multiplier": 1.15},
    10: {"name": "Favoriten", "multiplier": 0.85},
    11: {"name": "Simmering", "multiplier": 0.80},
    12: {"name": "Meidling", "multiplier": 0.90},
    13: {"name": "Hietzing", "multiplier": 1.10},
    14: {"name": "Penzing", "multiplier": 0.95},
    15: {"name": "Rudolfsheim-Fünfhaus", "multiplier": 0.85},
    16: {"name": "Ottakring", "multiplier": 0.90},
    17: {"name": "Hernals", "multiplier": 0.90},
    18: {"name": "Währing", "multiplier": 1.10},
    19: {"name": "Döbling", "multiplier": 1.15},
    20: {"name": "Brigittenau", "multiplier": 0.85},
    21: {"name": "Floridsdorf", "multiplier": 0.85},
    22: {"name": "Donaustadt", "multiplier": 0.90},
    23: {"name": "Liesing", "multiplier": 0.90},
}

# Default rent per sqm by city/region (EUR)
RENT_PER_SQM_DEFAULTS: Dict[str, float] = {
    "default": 12.0,
    "vienna_inner": 16.0,  # Districts 1-9
    "vienna_outer": 13.0,  # Districts 10-23
    "graz": 11.0,
    "linz": 10.5,
    "salzburg": 14.0,
    "innsbruck": 15.0,
    "klagenfurt": 9.5,
    "st_poelten": 9.0,
    "eisenstadt": 8.5,
}

# Average price per sqm by Vienna district (EUR, approximate market data)
VIENNA_PRICE_PER_SQM: Dict[int, float] = {
    1: 12000,
    2: 5500,
    3: 6000,
    4: 6500,
    5: 5000,
    6: 6000,
    7: 6500,
    8: 6500,
    9: 6000,
    10: 3800,
    11: 3500,
    12: 4200,
    13: 6000,
    14: 4500,
    15: 4000,
    16: 4200,
    17: 4500,
    18: 5500,
    19: 6000,
    20: 4000,
    21: 4000,
    22: 4200,
    23: 4500,
}

# Transaction costs in Austria (percentage of purchase price)
TRANSACTION_COSTS: Dict[str, float] = {
    "grunderwerbsteuer": 3.5,  # Property transfer tax
    "grundbuch": 1.1,  # Land registry fee
    "notar": 1.0,  # Notary fees (approx)
    "makler": 3.0,  # Broker fee (max, often negotiable or 0)
}

# MRG (Mietrechtsgesetz) applicability based on building age
MRG_BUILDING_CUTOFF_YEAR = 1945  # Buildings before this are typically MRG-regulated


class InvestmentRecommendation(Enum):
    """Investment recommendation levels."""

    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    CONSIDER = "CONSIDER"
    WEAK = "WEAK"
    AVOID = "AVOID"


# Score thresholds for recommendations
RECOMMENDATION_THRESHOLDS: Dict[InvestmentRecommendation, tuple] = {
    InvestmentRecommendation.STRONG_BUY: (8.0, 10.0),
    InvestmentRecommendation.BUY: (6.5, 8.0),
    InvestmentRecommendation.CONSIDER: (5.0, 6.5),
    InvestmentRecommendation.WEAK: (3.5, 5.0),
    InvestmentRecommendation.AVOID: (0.0, 3.5),
}

# Austrian states (Bundesländer) with abbreviations
AUSTRIAN_STATES: Dict[str, str] = {
    "W": "Wien",
    "NÖ": "Niederösterreich",
    "OÖ": "Oberösterreich",
    "S": "Salzburg",
    "T": "Tirol",
    "V": "Vorarlberg",
    "K": "Kärnten",
    "ST": "Steiermark",
    "B": "Burgenland",
}

# Postal code ranges by state
POSTAL_CODE_RANGES: Dict[str, tuple] = {
    "Wien": (1010, 1239),
    "Niederösterreich": (2000, 3999),
    "Oberösterreich": (4000, 4999),
    "Salzburg": (5000, 5999),
    "Tirol": (6000, 6999),
    "Vorarlberg": (6800, 6999),
    "Kärnten": (9000, 9999),
    "Steiermark": (8000, 8999),
    "Burgenland": (7000, 7999),
}
