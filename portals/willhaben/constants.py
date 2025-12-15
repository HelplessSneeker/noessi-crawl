"""Willhaben.at portal-specific constants."""

from typing import Dict

# Area ID to Location mapping for willhaben.at
# Maps willhaben search area_ids to postal codes and cities
AREA_ID_TO_LOCATION: Dict[int, Dict[str, str]] = {
    # Vienna districts (area_ids 201-223 map to districts 1-23)
    201: {"postal_code": "1010", "city": "Wien", "district_number": 1},
    202: {"postal_code": "1020", "city": "Wien", "district_number": 2},
    203: {"postal_code": "1030", "city": "Wien", "district_number": 3},
    204: {"postal_code": "1040", "city": "Wien", "district_number": 4},
    205: {"postal_code": "1050", "city": "Wien", "district_number": 5},
    206: {"postal_code": "1060", "city": "Wien", "district_number": 6},
    207: {"postal_code": "1070", "city": "Wien", "district_number": 7},
    208: {"postal_code": "1080", "city": "Wien", "district_number": 8},
    209: {"postal_code": "1090", "city": "Wien", "district_number": 9},
    210: {"postal_code": "1100", "city": "Wien", "district_number": 10},
    211: {"postal_code": "1110", "city": "Wien", "district_number": 11},
    212: {"postal_code": "1120", "city": "Wien", "district_number": 12},
    213: {"postal_code": "1130", "city": "Wien", "district_number": 13},
    214: {"postal_code": "1140", "city": "Wien", "district_number": 14},
    215: {"postal_code": "1150", "city": "Wien", "district_number": 15},
    216: {"postal_code": "1160", "city": "Wien", "district_number": 16},
    217: {"postal_code": "1170", "city": "Wien", "district_number": 17},
    218: {"postal_code": "1180", "city": "Wien", "district_number": 18},
    219: {"postal_code": "1190", "city": "Wien", "district_number": 19},
    220: {"postal_code": "1200", "city": "Wien", "district_number": 20},
    221: {"postal_code": "1210", "city": "Wien", "district_number": 21},
    222: {"postal_code": "1220", "city": "Wien", "district_number": 22},
    223: {"postal_code": "1230", "city": "Wien", "district_number": 23},
    # Klagenfurt (Kärnten)
    117223: {"postal_code": "9020", "city": "Klagenfurt"},
    117224: {"postal_code": "9061", "city": "Klagenfurt"},
    117225: {"postal_code": "9073", "city": "Klagenfurt"},
    # Villach (Kärnten)
    117226: {"postal_code": "9500", "city": "Villach"},
    117227: {"postal_code": "9504", "city": "Villach"},
    117228: {"postal_code": "9523", "city": "Villach"},
    # Austrian province capitals
    # Linz (Oberösterreich)
    400: {"postal_code": "4020", "city": "Linz"},
    # Graz (Steiermark)
    300: {"postal_code": "8010", "city": "Graz"},
    # Salzburg (Salzburg)
    500: {"postal_code": "5020", "city": "Salzburg"},
    # Innsbruck (Tirol)
    600: {"postal_code": "6020", "city": "Innsbruck"},
    # Bregenz (Vorarlberg)
    700: {"postal_code": "6900", "city": "Bregenz"},
    # St. Pölten (Niederösterreich)
    310: {"postal_code": "3100", "city": "St. Pölten"},
    # Eisenstadt (Burgenland)
    710: {"postal_code": "7000", "city": "Eisenstadt"},
}

# Reverse mapping: PLZ to area_id for willhaben.at
# This allows users to specify postal codes in config instead of portal-specific area_ids
PLZ_TO_AREA_ID: Dict[str, int] = {
    # Vienna districts (PLZ to area_id)
    "1010": 201,
    "1020": 202,
    "1030": 203,
    "1040": 204,
    "1050": 205,
    "1060": 206,
    "1070": 207,
    "1080": 208,
    "1090": 209,
    "1100": 210,
    "1110": 211,
    "1120": 212,
    "1130": 213,
    "1140": 214,
    "1150": 215,
    "1160": 216,
    "1170": 217,
    "1180": 218,
    "1190": 219,
    "1200": 220,
    "1210": 221,
    "1220": 222,
    "1230": 223,
    # Klagenfurt
    "9020": 117223,
    "9061": 117224,
    "9073": 117225,
    # Villach
    "9500": 117226,
    "9504": 117227,
    "9523": 117228,
    # Austrian province capitals
    "4020": 400,  # Linz
    "8010": 300,  # Graz
    "5020": 500,  # Salzburg
    "6020": 600,  # Innsbruck
    "6900": 700,  # Bregenz
    "3100": 310,  # St. Pölten
    "7000": 710,  # Eisenstadt
}
