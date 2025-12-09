"""German translations for output generation."""

from typing import Dict

# Main section headers
HEADERS: Dict[str, str] = {
    "investment_summary": "Investitions-Zusammenfassung",
    "investment_summary_report": "Investitions-Zusammenfassung Bericht",
    "financial_analysis": "Finanzanalyse",
    "property_details": "Objektdetails",
    "location": "Lage",
    "features": "Ausstattung",
    "energy": "Energie",
    "investment_analysis": "Investitionsanalyse",
    "positive_factors": "Positive Faktoren",
    "risk_factors": "Risikofaktoren",
    "regulatory_notes": "Regulatorische Hinweise",
    "next_steps": "Nächste Schritte",
    "top_opportunities": "Top Investitionsmöglichkeiten",
    "llm_summary_section": "KI-gestützte Zusammenfassung",
}

# Field labels
LABELS: Dict[str, str] = {
    # Basic info
    "generated": "Erstellt",
    "run_id": "Lauf-ID",
    "portal": "Portal",
    "area_ids": "Bereichs-IDs",
    "max_price": "Max. Preis",
    "total_scraped": "Gesamt gescannt",
    "active": "Aktiv",
    "rejected": "Abgelehnt",
    "top": "Top",
    # Financial
    "price": "Preis",
    "price_per_sqm": "Preis pro m²",
    "size": "Größe",
    "size_sqm": "Größe (m²)",
    "yield": "Rendite",
    "gross_yield": "Bruttorendite",
    "net_yield": "Nettorendite",
    "estimated_rent": "Geschätzte Miete",
    "monthly_rent": "Monatliche Miete",
    "operating_costs": "Betriebskosten",
    "betriebskosten": "Betriebskosten",
    "betriebskosten_monthly": "Monatliche Betriebskosten",
    "operating_costs_per_sqm": "Betriebskosten pro m²",
    "reserve_fund": "Reparaturrücklage",
    "reparaturrucklage": "Reparaturrücklage",
    "total_monthly_costs": "Gesamte monatliche Kosten",
    "annual_costs": "Jährliche Kosten",
    "annual_income": "Jährliche Einnahmen",
    "cash_flow": "Cashflow",
    "cash_flow_monthly": "Monatlicher Cashflow",
    "monthly_payment": "Monatliche Rate",
    "down_payment": "Eigenkapital",
    "loan_amount": "Kreditbetrag",
    "transaction_costs": "Transaktionskosten",
    "total_investment": "Gesamtinvestition",
    # Property details
    "rooms": "Zimmer",
    "floor": "Stockwerk",
    "total_floors": "Stockwerke gesamt",
    "year_built": "Baujahr",
    "condition": "Zustand",
    "building_type": "Gebäudetyp",
    "available_from": "Verfügbar ab",
    # Location
    "location": "Lage",
    "city": "Stadt",
    "district": "Bezirk",
    "postal_code": "PLZ",
    "postal_codes": "Postleitzahlen",
    "address": "Adresse",
    "full_address": "Vollständige Adresse",
    # Features
    "elevator": "Aufzug",
    "balcony": "Balkon",
    "terrace": "Terrasse",
    "garden": "Garten",
    "parking": "Parkplatz",
    "garage": "Garage",
    "basement": "Keller",
    "furnished": "Möbliert",
    "pets_allowed": "Haustiere erlaubt",
    # Energy
    "energy_rating": "Energieklasse",
    "energy_class": "Energieklasse",
    "hwb": "HWB",
    "hwb_value": "HWB-Wert",
    "heating": "Heizung",
    "heating_type": "Heizungsart",
    # Other
    "title": "Titel",
    "description": "Beschreibung",
    "investment_score": "Investitionsbewertung",
    "recommendation": "Empfehlung",
    "source": "Quelle",
    "scraped": "Gescannt",
    "listing_id": "Inserats-ID",
    "details": "Details",
    "rank": "Rang",
    "score": "Bewertung",
}

# Table headers for summary report
TABLE_HEADERS: Dict[str, str] = {
    "rank": "Rang",
    "score": "Bewertung",
    "recommendation": "Empfehlung",
    "price": "Preis",
    "size": "Größe",
    "yield": "Rendite",
    "location": "Lage",
    "details": "Details",
    "source": "Quelle",
}

# Investment recommendations
RECOMMENDATIONS: Dict[str, str] = {
    "STRONG BUY": "STARKER KAUF",
    "BUY": "KAUFEN",
    "CONSIDER": "ERWÄGEN",
    "WEAK": "SCHWACH",
    "AVOID": "VERMEIDEN",
}

# Next steps checklist
NEXT_STEPS: list[str] = [
    "Besichtigung vereinbaren",
    "Gebäudedokumentation anfordern",
    "Aufschlüsselung der Betriebskosten überprüfen",
    "Mietmarkt für vergleichbare Wohnungen prüfen",
    "Grundbuch überprüfen",
]

# Yes/No translations
BOOLEAN: Dict[str, str] = {
    "yes": "Ja",
    "no": "Nein",
    "true": "Ja",
    "false": "Nein",
    "available": "Vorhanden",
    "not_available": "Nicht vorhanden",
}

# Common phrases
PHRASES: Dict[str, str] = {
    "generated_by": "Erstellt von Enhanced Apartment Scraper",
    "mrg_notice": "Diese Immobilie kann aufgrund des Baualters dem MRG-Mietpreisrecht (Mietrechtsgesetz) unterliegen.",
    "commission_free": "Provisionsfrei",
    "broker_commission": "Maklerprovision",
    "n/a": "k.A.",  # keine Angabe
}

# Property condition translations (extending constants.py)
CONDITION_TRANSLATIONS: Dict[str, str] = {
    "First occupancy": "Erstbezug",
    "First occupancy after renovation": "Erstbezug nach Sanierung",
    "Renovated": "Saniert",
    "Needs renovation": "Renovierungsbedürftig",
    "Good condition": "Guter Zustand",
    "Very good condition": "Sehr guter Zustand",
    "Like new": "Neuwertig",
    "Well maintained": "Gepflegt",
}

# Building type translations
BUILDING_TYPE_TRANSLATIONS: Dict[str, str] = {
    "Old building (pre-1945)": "Altbau (vor 1945)",
    "New building (post-1945)": "Neubau (nach 1945)",
    "Gründerzeit (1848-1918)": "Gründerzeit (1848-1918)",
    "Interwar period (1918-1945)": "Zwischenkrieg (1918-1945)",
    "Post-war (1945-1970)": "Nachkrieg (1945-1970)",
    "Modern (post-1970)": "Modern (nach 1970)",
}

# Parking type translations
PARKING_TRANSLATIONS: Dict[str, str] = {
    "Underground garage": "Tiefgarage",
    "Garage": "Garage",
    "Parking space": "Stellplatz",
    "Carport": "Carport",
    "Parking lot": "Parkplatz",
    "No parking": "Kein Parkplatz",
}

# Heating type translations
HEATING_TRANSLATIONS: Dict[str, str] = {
    "District heating": "Fernwärme",
    "Gas heating": "Gasheizung",
    "Central heating": "Zentralheizung",
    "Floor heating": "Etagenheizung",
    "Underfloor heating": "Fußbodenheizung",
    "Electric heating": "Elektroheizung",
    "Oil heating": "Ölheizung",
    "Pellet heating": "Pelletsheizung",
    "Heat pump": "Wärmepumpe",
    "Solar heating": "Solarheizung",
}

# Financial analysis section translations
FINANCIAL_LABELS: Dict[str, str] = {
    "purchase_analysis": "Kaufanalyse",
    "monthly_costs": "Monatliche Kosten",
    "rental_analysis": "Mietanalyse",
    "investment_metrics": "Investitionskennzahlen",
    "mortgage_calculation": "Hypothekenberechnung",
}
