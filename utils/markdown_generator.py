"""Markdown file generation for apartment listings."""

import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

from models.apartment import ApartmentListing
from utils.translations import (
    BOOLEAN,
    BUILDING_TYPE_TRANSLATIONS,
    CONDITION_TRANSLATIONS,
    HEADERS,
    HEATING_TRANSLATIONS,
    LABELS,
    NEXT_STEPS,
    PARKING_TRANSLATIONS,
    PHRASES,
    RECOMMENDATIONS,
)


class MarkdownGenerator:
    """Generator for individual apartment markdown files with YAML frontmatter."""

    def __init__(self, output_dir: str = "output/apartments"):
        """
        Initialize the generator.

        Args:
            output_dir: Base output directory for apartment files
        """
        self.output_dir = output_dir
        # Note: active_dir and rejected_dir are deprecated
        # New architecture uses flat apartments/ folder with immediate saving

    def generate_filename(self, apartment: ApartmentListing) -> str:
        """
        Generate a descriptive filename for the apartment.

        Format: YYYY-MM-DD_city_district_street_price.md
        """
        parts = []

        # Date
        date_str = apartment.scraped_at.strftime("%Y-%m-%d")
        parts.append(date_str)

        # City
        if apartment.city:
            city = self._sanitize_filename(apartment.city)
            parts.append(city)

        # District
        if apartment.district_number:
            parts.append(f"bez{apartment.district_number}")
        elif apartment.district:
            district = self._sanitize_filename(apartment.district)
            parts.append(district)

        # Street (first part only)
        if apartment.street:
            street = self._sanitize_filename(apartment.street.split()[0])
            parts.append(street)

        # Price in thousands
        if apartment.price:
            price_k = int(apartment.price / 1000)
            parts.append(f"{price_k}k")

        # Fallback to listing ID if not enough parts
        if len(parts) < 3:
            parts.append(apartment.listing_id[:8])

        filename = "_".join(parts) + ".md"
        return filename.lower()

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename."""
        # Remove umlauts
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "Ä": "Ae",
            "Ö": "Oe",
            "Ü": "Ue",
            "ß": "ss",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Keep only alphanumeric and convert spaces to underscores
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s]+", "_", text)
        return text.strip("_")

    def generate_yaml_frontmatter(self, apartment: ApartmentListing) -> str:
        """Generate YAML frontmatter for the apartment."""
        frontmatter: Dict[str, Any] = {
            "listing_id": apartment.listing_id,
            "source_url": apartment.source_url,
            "scraped_at": apartment.scraped_at.isoformat(),
        }

        # Location
        location = {}
        if apartment.city:
            location["city"] = apartment.city
        if apartment.district:
            location["district"] = apartment.district
        if apartment.district_number:
            location["district_number"] = apartment.district_number
        if apartment.postal_code:
            location["postal_code"] = apartment.postal_code
        if apartment.street:
            location["street"] = apartment.street
        if apartment.house_number:
            location["house_number"] = apartment.house_number
        if apartment.state:
            location["state"] = apartment.state
        if location:
            frontmatter["location"] = location

        # Price
        price_info = {}
        if apartment.price:
            price_info["amount"] = apartment.price
            price_info["currency"] = "EUR"
        if apartment.price_per_sqm:
            price_info["per_sqm"] = apartment.price_per_sqm
        if price_info:
            frontmatter["price"] = price_info

        # Costs
        costs = {}
        if apartment.betriebskosten_monthly:
            costs["betriebskosten"] = apartment.betriebskosten_monthly
        if apartment.betriebskosten_per_sqm:
            costs["betriebskosten_per_sqm"] = apartment.betriebskosten_per_sqm
        if apartment.reparaturrucklage:
            costs["reparaturrucklage"] = apartment.reparaturrucklage
        if apartment.heating_cost_monthly:
            costs["heating"] = apartment.heating_cost_monthly
        if costs:
            frontmatter["costs"] = costs

        # Property specs
        specs = {}
        if apartment.size_sqm:
            specs["size_sqm"] = apartment.size_sqm
        if apartment.rooms:
            specs["rooms"] = apartment.rooms
        if apartment.bedrooms:
            specs["bedrooms"] = apartment.bedrooms
        if apartment.bathrooms:
            specs["bathrooms"] = apartment.bathrooms
        if apartment.floor is not None:
            specs["floor"] = apartment.floor
        if apartment.floor_text:
            specs["floor_text"] = apartment.floor_text
        if apartment.total_floors:
            specs["total_floors"] = apartment.total_floors
        if apartment.year_built:
            specs["year_built"] = apartment.year_built
        if apartment.condition:
            specs["condition"] = apartment.condition
        if apartment.building_type:
            specs["building_type"] = apartment.building_type
        if specs:
            frontmatter["property"] = specs

        # Features
        features = {}
        if apartment.elevator is not None:
            features["elevator"] = apartment.elevator
        if apartment.balcony is not None:
            features["balcony"] = apartment.balcony
        if apartment.terrace is not None:
            features["terrace"] = apartment.terrace
        if apartment.loggia is not None:
            features["loggia"] = apartment.loggia
        if apartment.garden is not None:
            features["garden"] = apartment.garden
        if apartment.parking:
            features["parking"] = apartment.parking
        if apartment.cellar is not None:
            features["cellar"] = apartment.cellar
        if apartment.storage is not None:
            features["storage"] = apartment.storage
        if apartment.barrier_free is not None:
            features["barrier_free"] = apartment.barrier_free
        if features:
            frontmatter["features"] = features

        # Energy
        energy = {}
        if apartment.energy_rating:
            energy["rating"] = apartment.energy_rating
        if apartment.hwb_value:
            energy["hwb"] = apartment.hwb_value
        if apartment.fgee_value:
            energy["fgee"] = apartment.fgee_value
        if apartment.heating_type:
            energy["heating_type"] = apartment.heating_type
        if energy:
            frontmatter["energy"] = energy

        # Investment metrics
        investment = {}
        if apartment.estimated_rent:
            investment["estimated_rent"] = apartment.estimated_rent
        if apartment.gross_yield:
            investment["gross_yield"] = apartment.gross_yield
        if apartment.net_yield:
            investment["net_yield"] = apartment.net_yield
        if apartment.cash_flow_monthly:
            investment["cash_flow"] = apartment.cash_flow_monthly
        if apartment.investment_score:
            investment["score"] = apartment.investment_score
        if apartment.recommendation:
            investment["recommendation"] = apartment.recommendation
        if investment:
            frontmatter["investment"] = investment

        # Regulatory
        regulatory = {}
        if apartment.mrg_applicable is not None:
            regulatory["mrg_applicable"] = apartment.mrg_applicable
        if apartment.commission_free is not None:
            regulatory["commission_free"] = apartment.commission_free
        if apartment.commission_percent:
            regulatory["commission_percent"] = apartment.commission_percent
        if regulatory:
            frontmatter["regulatory"] = regulatory

        # Tags for searchability
        tags = self._generate_tags(apartment)
        if tags:
            frontmatter["tags"] = tags

        return yaml.dump(
            frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
        )

    def _generate_tags(self, apartment: ApartmentListing) -> list:
        """Generate tags for the apartment."""
        tags = []

        # Location tags
        if apartment.city:
            tags.append(apartment.city.lower())
        if apartment.district_number:
            tags.append(f"bezirk-{apartment.district_number}")

        # Price range tags
        if apartment.price:
            if apartment.price < 150000:
                tags.append("budget")
            elif apartment.price < 250000:
                tags.append("mid-range")
            elif apartment.price < 400000:
                tags.append("premium")
            else:
                tags.append("luxury")

        # Size tags
        if apartment.size_sqm:
            if apartment.size_sqm < 50:
                tags.append("compact")
            elif apartment.size_sqm < 80:
                tags.append("medium")
            else:
                tags.append("spacious")

        # Feature tags
        if apartment.balcony:
            tags.append("balcony")
        if apartment.terrace:
            tags.append("terrace")
        if apartment.garden:
            tags.append("garden")
        if apartment.elevator:
            tags.append("elevator")
        if apartment.parking:
            tags.append("parking")

        # Investment tags
        if apartment.recommendation:
            tags.append(apartment.recommendation.lower().replace(" ", "-"))
        if apartment.gross_yield and apartment.gross_yield >= 5:
            tags.append("high-yield")

        return tags

    def generate_markdown_content(self, apartment: ApartmentListing) -> str:
        """Generate the markdown body content."""
        content = []

        # Title
        title = apartment.title or f"Wohnung in {apartment.city or 'Unbekannt'}"
        content.append(f"# {title}\n")

        # Executive summary
        content.append(f"## {HEADERS['investment_summary']}\n")
        summary_parts = []
        # Size (critical field)
        if apartment.size_sqm and apartment.size_sqm >= 10:
            summary_parts.append(f"{apartment.size_sqm:.0f} m²")
        else:
            summary_parts.append("n/a m²")
        if apartment.rooms:
            summary_parts.append(f"{apartment.rooms} {LABELS['rooms']}")
        # Price (critical field)
        if apartment.price and apartment.price > 0:
            summary_parts.append(f"EUR {apartment.price:,.0f}")
        else:
            summary_parts.append("EUR n/a")

        # Location: just city (keep it simple)
        if apartment.city:
            summary_parts.append(apartment.city)

        if summary_parts:
            content.append(" | ".join(summary_parts) + "\n")

        if apartment.recommendation and apartment.investment_score:
            # Translate recommendation to German
            recommendation_de = RECOMMENDATIONS.get(
                apartment.recommendation, apartment.recommendation
            )
            content.append(
                f"\n**{LABELS['investment_score']}: {apartment.investment_score:.1f}/10** - "
                f"**{recommendation_de}**\n"
            )

        # Financial analysis
        content.append(f"\n## {HEADERS['financial_analysis']}\n")
        content.append(f"| Kennzahl | Wert |")
        content.append("|--------|-------|")

        # Price (critical field)
        if apartment.price and apartment.price > 0:
            content.append(f"| {LABELS['price']} | EUR {apartment.price:,.0f} |")
        else:
            content.append(f"| {LABELS['price']} | n/a |")

        # Price per sqm
        if apartment.price_per_sqm:
            content.append(
                f"| {LABELS['price_per_sqm']} | EUR {apartment.price_per_sqm:,.0f} |"
            )

        # Betriebskosten (critical field)
        if apartment.betriebskosten_monthly and apartment.betriebskosten_monthly > 0:
            content.append(
                f"| {LABELS['betriebskosten']} | EUR {apartment.betriebskosten_monthly:,.0f}/Monat |"
            )
        else:
            content.append(
                f"| {LABELS['betriebskosten']} | n/a |"
            )
        if apartment.estimated_rent:
            content.append(
                f"| {LABELS['estimated_rent']} | EUR {apartment.estimated_rent:,.0f}/Monat |"
            )
        if apartment.gross_yield:
            content.append(
                f"| {LABELS['gross_yield']} | {apartment.gross_yield:.2f}% |"
            )
        if apartment.net_yield:
            content.append(f"| {LABELS['net_yield']} | {apartment.net_yield:.2f}% |")
        if apartment.cash_flow_monthly is not None:
            content.append(
                f"| {LABELS['cash_flow']} | EUR {apartment.cash_flow_monthly:,.0f}/Monat |"
            )

        content.append("")

        # Property details
        content.append(f"\n## {HEADERS['property_details']}\n")

        # Specifications
        content.append("### Spezifikationen\n")
        specs_table = []
        # Size (critical field)
        if apartment.size_sqm and apartment.size_sqm >= 10:
            specs_table.append(f"- **{LABELS['size']}:** {apartment.size_sqm:.0f} m²")
        else:
            specs_table.append(f"- **{LABELS['size']}:** n/a")
        if apartment.rooms:
            specs_table.append(f"- **{LABELS['rooms']}:** {apartment.rooms}")
        if apartment.floor_text:
            specs_table.append(f"- **{LABELS['floor']}:** {apartment.floor_text}")
        elif apartment.floor is not None:
            floor_text = (
                "Erdgeschoss" if apartment.floor == 0 else f"Stock {apartment.floor}"
            )
            specs_table.append(f"- **{LABELS['floor']}:** {floor_text}")
        if apartment.year_built:
            specs_table.append(f"- **{LABELS['year_built']}:** {apartment.year_built}")
        if apartment.condition:
            # Translate condition to German if in English
            condition_de = CONDITION_TRANSLATIONS.get(
                apartment.condition, apartment.condition
            )
            specs_table.append(f"- **{LABELS['condition']}:** {condition_de}")
        if apartment.building_type:
            # Translate building type to German if in English
            building_type_de = BUILDING_TYPE_TRANSLATIONS.get(
                apartment.building_type, apartment.building_type
            )
            specs_table.append(f"- **{LABELS['building_type']}:** {building_type_de}")

        if specs_table:
            content.extend(specs_table)
            content.append("")

        # Features
        features = []
        if apartment.elevator:
            features.append(LABELS["elevator"])
        if apartment.balcony:
            features.append(LABELS["balcony"])
        if apartment.terrace:
            features.append(LABELS["terrace"])
        if apartment.loggia:
            features.append("Loggia")
        if apartment.garden:
            features.append(LABELS["garden"])
        if apartment.parking:
            parking_de = PARKING_TRANSLATIONS.get(apartment.parking, apartment.parking)
            features.append(f"{LABELS['parking']} ({parking_de})")
        if apartment.cellar:
            features.append(LABELS["basement"])
        if apartment.storage:
            features.append("Abstellraum")
        if apartment.barrier_free:
            features.append("Barrierefrei")

        if features:
            content.append(f"### {HEADERS['features']}\n")
            content.append(", ".join(features) + "\n")

        # Energy
        if apartment.energy_rating or apartment.hwb_value or apartment.heating_type:
            content.append(f"### {HEADERS['energy']}\n")
            if apartment.energy_rating:
                content.append(
                    f"- **{LABELS['energy_class']}:** {apartment.energy_rating}"
                )
            if apartment.hwb_value:
                content.append(f"- **{LABELS['hwb']}:** {apartment.hwb_value} kWh/m²a")
            if apartment.heating_type:
                heating_de = HEATING_TRANSLATIONS.get(
                    apartment.heating_type, apartment.heating_type
                )
                content.append(f"- **{LABELS['heating']}:** {heating_de}")
            content.append("")

        # Location - Simplified: just show the extracted address
        content.append(f"\n## {HEADERS['location']}\n")
        content.append(f"**{LABELS['location']}:**  \n")

        # Build address from components (street address if available)
        if apartment.street:
            street_line = apartment.street
            if apartment.house_number:
                street_line += f" {apartment.house_number}"
            if apartment.door_number:
                street_line += f"/{apartment.door_number}"
            content.append(street_line + "  ")

        # City line with postal code
        city_parts = []
        if apartment.postal_code:
            city_parts.append(apartment.postal_code)
        if apartment.city:
            city_parts.append(apartment.city)

        if city_parts:
            content.append(" ".join(city_parts) + "\n")
        elif apartment.full_address:
            # Fallback to full_address if we don't have structured data
            content.append(apartment.full_address + "\n")
        else:
            content.append(PHRASES["n/a"] + "\n")

        # Investment analysis
        if apartment.positive_factors or apartment.risk_factors:
            content.append(f"\n## {HEADERS['investment_analysis']}\n")

            if apartment.positive_factors:
                content.append(f"### {HEADERS['positive_factors']}\n")
                for factor in apartment.positive_factors:
                    content.append(f"- {factor}")
                content.append("")

            if apartment.risk_factors:
                content.append(f"### {HEADERS['risk_factors']}\n")
                for factor in apartment.risk_factors:
                    content.append(f"- {factor}")
                content.append("")

        # Warning for missing betriebskosten
        if apartment.betriebskosten_monthly is None:
            content.append("\n---\n")
            content.append("### ⚠️ Wichtiger Hinweis\n")
            content.append(
                f"**Betriebskosten konnten nicht automatisch extrahiert werden.** "
                f"Bitte prüfen Sie diese Information manuell auf der [Willhaben-Seite]({apartment.source_url}).\n"
            )
            content.append("")

        # Regulatory
        if (
            apartment.mrg_applicable is not None
            or apartment.commission_free is not None
        ):
            content.append(f"\n## {HEADERS['regulatory_notes']}\n")
            if apartment.mrg_applicable:
                content.append(f"- {PHRASES['mrg_notice']}\n")
            if apartment.commission_free:
                content.append(f"- {PHRASES['commission_free']}\n")
            elif apartment.commission_percent:
                content.append(
                    f"- {PHRASES['broker_commission']}: {apartment.commission_percent}%\n"
                )

        # Next steps
        content.append(f"\n## {HEADERS['next_steps']}\n")
        for step in NEXT_STEPS:
            content.append(f"- [ ] {step}")
        content.append("")

        # Source
        content.append("\n---\n")
        content.append(
            f"{LABELS['source']}: [{apartment.source_portal}]({apartment.source_url})"
        )
        content.append(
            f"  \n{LABELS['scraped']}: {apartment.scraped_at.strftime('%Y-%m-%d %H:%M')}"
        )

        return "\n".join(content)

    def generate_apartment_file(
        self,
        apartment: ApartmentListing,
        rejected: bool = False,
        rejection_reason: Optional[str] = None,
    ) -> str:
        """
        Generate a complete markdown file for an apartment.

        Args:
            apartment: The apartment listing
            rejected: If True, save to rejected folder
            rejection_reason: Reason for rejection (if rejected)

        Returns:
            Path to the generated file
        """
        # Generate filename
        filename = self.generate_filename(apartment)
        # Note: rejected parameter is deprecated, now uses flat output_dir structure
        filepath = os.path.join(self.output_dir, filename)

        # Generate content
        frontmatter = self.generate_yaml_frontmatter(apartment)
        body = self.generate_markdown_content(apartment)

        # Add rejection note if applicable
        if rejected and rejection_reason:
            body = f"> **Abgelehnt:** {rejection_reason}\n\n" + body

        # Combine into full document
        full_content = f"---\n{frontmatter}---\n\n{body}"

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        return filepath
