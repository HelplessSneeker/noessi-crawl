"""Markdown file generation for apartment listings."""

import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

from models.apartment import ApartmentListing


class MarkdownGenerator:
    """Generator for individual apartment markdown files with YAML frontmatter."""

    def __init__(self, output_dir: str = "output/apartments"):
        """
        Initialize the generator.

        Args:
            output_dir: Base output directory for apartment files
        """
        self.output_dir = output_dir
        self.active_dir = os.path.join(output_dir, "active")
        self.rejected_dir = os.path.join(output_dir, "rejected")

        # Ensure directories exist
        os.makedirs(self.active_dir, exist_ok=True)
        os.makedirs(self.rejected_dir, exist_ok=True)

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
        title = apartment.title or f"Apartment in {apartment.city or 'Unknown'}"
        content.append(f"# {title}\n")

        # Executive summary
        content.append("## Summary\n")
        summary_parts = []
        if apartment.size_sqm:
            summary_parts.append(f"{apartment.size_sqm:.0f} m2")
        if apartment.rooms:
            summary_parts.append(f"{apartment.rooms} rooms")
        if apartment.price:
            summary_parts.append(f"EUR {apartment.price:,.0f}")
        if apartment.district:
            summary_parts.append(f"{apartment.district}")
        elif apartment.city:
            summary_parts.append(apartment.city)

        if summary_parts:
            content.append(" | ".join(summary_parts) + "\n")

        if apartment.recommendation and apartment.investment_score:
            content.append(
                f"\n**Investment Score: {apartment.investment_score:.1f}/10** - "
                f"**{apartment.recommendation}**\n"
            )

        # Financial analysis
        content.append("\n## Financial Analysis\n")
        content.append("| Metric | Value |")
        content.append("|--------|-------|")

        if apartment.price:
            content.append(f"| Purchase Price | EUR {apartment.price:,.0f} |")
        if apartment.price_per_sqm:
            content.append(f"| Price/m2 | EUR {apartment.price_per_sqm:,.0f} |")
        if apartment.betriebskosten_monthly:
            content.append(
                f"| Operating Costs | EUR {apartment.betriebskosten_monthly:,.0f}/month |"
            )
        if apartment.estimated_rent:
            content.append(
                f"| Estimated Rent | EUR {apartment.estimated_rent:,.0f}/month |"
            )
        if apartment.gross_yield:
            content.append(f"| Gross Yield | {apartment.gross_yield:.2f}% |")
        if apartment.net_yield:
            content.append(f"| Net Yield | {apartment.net_yield:.2f}% |")
        if apartment.cash_flow_monthly is not None:
            content.append(
                f"| Est. Cash Flow | EUR {apartment.cash_flow_monthly:,.0f}/month |"
            )

        content.append("")

        # Property details
        content.append("\n## Property Details\n")

        # Specifications
        content.append("### Specifications\n")
        specs_table = []
        if apartment.size_sqm:
            specs_table.append(f"- **Size:** {apartment.size_sqm:.0f} m2")
        if apartment.rooms:
            specs_table.append(f"- **Rooms:** {apartment.rooms}")
        if apartment.floor_text:
            specs_table.append(f"- **Floor:** {apartment.floor_text}")
        elif apartment.floor is not None:
            floor_text = (
                "Ground floor" if apartment.floor == 0 else f"Floor {apartment.floor}"
            )
            specs_table.append(f"- **Floor:** {floor_text}")
        if apartment.year_built:
            specs_table.append(f"- **Year Built:** {apartment.year_built}")
        if apartment.condition:
            specs_table.append(f"- **Condition:** {apartment.condition}")
        if apartment.building_type:
            specs_table.append(f"- **Building Type:** {apartment.building_type}")

        if specs_table:
            content.extend(specs_table)
            content.append("")

        # Features
        features = []
        if apartment.elevator:
            features.append("Elevator")
        if apartment.balcony:
            features.append("Balcony")
        if apartment.terrace:
            features.append("Terrace")
        if apartment.loggia:
            features.append("Loggia")
        if apartment.garden:
            features.append("Garden")
        if apartment.parking:
            features.append(f"Parking ({apartment.parking})")
        if apartment.cellar:
            features.append("Cellar")
        if apartment.storage:
            features.append("Storage")
        if apartment.barrier_free:
            features.append("Barrier-free")

        if features:
            content.append("### Features\n")
            content.append(", ".join(features) + "\n")

        # Energy
        if apartment.energy_rating or apartment.hwb_value or apartment.heating_type:
            content.append("### Energy\n")
            if apartment.energy_rating:
                content.append(f"- **Energy Class:** {apartment.energy_rating}")
            if apartment.hwb_value:
                content.append(f"- **HWB:** {apartment.hwb_value} kWh/m2a")
            if apartment.heating_type:
                content.append(f"- **Heating:** {apartment.heating_type}")
            content.append("")

        # Location
        content.append("\n## Location\n")

        # Always show city and postal code first
        if apartment.city or apartment.postal_code:
            location_line = []
            if apartment.postal_code:
                location_line.append(apartment.postal_code)
            if apartment.city:
                location_line.append(apartment.city)
            content.append(f"**City:** {' '.join(location_line)}\n")

        # District info
        if apartment.district or apartment.district_number:
            district_str = ""
            if apartment.district:
                district_str = apartment.district
            if apartment.district_number:
                if district_str:
                    district_str += f" ({apartment.district_number}. Bezirk)"
                else:
                    district_str = f"{apartment.district_number}. Bezirk"
            content.append(f"**District:** {district_str}\n")

        # Full address
        if apartment.full_address:
            content.append(f"**Address:** {apartment.full_address}\n")
        elif apartment.street:
            addr_parts = []
            street_full = apartment.street
            if apartment.house_number:
                street_full += f" {apartment.house_number}"
            if apartment.door_number:
                street_full += f"/{apartment.door_number}"
            addr_parts.append(street_full)
            content.append(f"**Address:** {', '.join(addr_parts)}\n")

        # Investment analysis
        if apartment.positive_factors or apartment.risk_factors:
            content.append("\n## Investment Analysis\n")

            if apartment.positive_factors:
                content.append("### Positive Factors\n")
                for factor in apartment.positive_factors:
                    content.append(f"- {factor}")
                content.append("")

            if apartment.risk_factors:
                content.append("### Risk Factors\n")
                for factor in apartment.risk_factors:
                    content.append(f"- {factor}")
                content.append("")

        # Regulatory
        if (
            apartment.mrg_applicable is not None
            or apartment.commission_free is not None
        ):
            content.append("\n## Regulatory Notes\n")
            if apartment.mrg_applicable:
                content.append(
                    "- This property may be subject to MRG rent control "
                    "(Mietrechtsgesetz) due to building age.\n"
                )
            if apartment.commission_free:
                content.append("- Commission-free purchase\n")
            elif apartment.commission_percent:
                content.append(
                    f"- Broker commission: {apartment.commission_percent}%\n"
                )

        # Next steps
        content.append("\n## Next Steps\n")
        content.append("- [ ] Schedule viewing")
        content.append("- [ ] Request building documentation")
        content.append("- [ ] Verify operating costs breakdown")
        content.append("- [ ] Check rental market for comparable units")
        content.append("- [ ] Review land registry (Grundbuch)")
        content.append("")

        # Source
        content.append("\n---\n")
        content.append(f"Source: [{apartment.source_portal}]({apartment.source_url})")
        content.append(
            f"  \nScraped: {apartment.scraped_at.strftime('%Y-%m-%d %H:%M')}"
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
        output_dir = self.rejected_dir if rejected else self.active_dir
        filepath = os.path.join(output_dir, filename)

        # Generate content
        frontmatter = self.generate_yaml_frontmatter(apartment)
        body = self.generate_markdown_content(apartment)

        # Add rejection note if applicable
        if rejected and rejection_reason:
            body = f"> **Rejected:** {rejection_reason}\n\n" + body

        # Combine into full document
        full_content = f"---\n{frontmatter}---\n\n{body}"

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        return filepath
