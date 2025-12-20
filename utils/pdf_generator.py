"""
PDF generator for apartment investment reports.
Creates professional PDF reports with clickable navigation from summary to apartment details.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fpdf import FPDF

from models.apartment import ApartmentListing
from utils.translations import HEADERS, LABELS, PHRASES, RECOMMENDATIONS, TABLE_HEADERS


class PDFGenerator:
    """
    Generates professional PDF reports for apartment investment analysis.

    Features:
    - First page: Summary table with investment rankings
    - Following pages: Detailed apartment analysis (one per page)
    - Two-column layout for apartment details
    - Clickable links from summary to details
    - Professional corporate styling (navy/gray color scheme)
    - German-language output matching markdown reports
    """

    # Professional color scheme
    NAVY = (26, 58, 82)  # #1a3a52 - Headers and emphasis
    GRAY = (108, 117, 125)  # #6c757d - Secondary text
    LIGHT_GRAY = (248, 249, 250)  # #f8f9fa - Table backgrounds
    WHITE = (255, 255, 255)

    # Score-based colors for recommendations
    COLOR_EXCELLENT = (40, 167, 69)  # Green - 8.0+
    COLOR_GOOD = (0, 123, 255)  # Blue - 6.5-8.0
    COLOR_AVERAGE = (255, 193, 7)  # Yellow - 5.0-6.5
    COLOR_WEAK = (253, 126, 20)  # Orange - 3.5-5.0
    COLOR_POOR = (220, 53, 69)  # Red - <3.5

    def __init__(self, output_dir: str, run_timestamp: datetime, config: Dict):
        """
        Initialize PDF generator.

        Args:
            output_dir: Directory for PDF output
            run_timestamp: Timestamp of scraping run
            config: Configuration dictionary
        """
        self.output_dir = Path(output_dir)
        self.run_timestamp = run_timestamp
        self.config = config

        # PDF settings
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=False, margin=15)

        # Link registry for internal navigation
        self.apartment_links: Dict[str, int] = {}  # listing_id -> link_id

        # Setup fonts and metadata
        self._setup_fonts_and_metadata()

    def _setup_fonts_and_metadata(self):
        """Configure PDF fonts and metadata."""
        # Add Unicode support for German characters
        self.pdf.add_font(
            "NotoSans", "", "/usr/share/fonts/noto/NotoSans-Regular.ttf", uni=True
        )
        self.pdf.add_font(
            "NotoSans", "B", "/usr/share/fonts/noto/NotoSans-Bold.ttf", uni=True
        )

        # Set metadata
        self.pdf.set_title("Immobilien Investment Bericht")
        self.pdf.set_author("Enhanced Apartment Scraper")
        self.pdf.set_creator("noessi-crawl")
        self.pdf.set_subject("Apartment Investment Analysis")

    def generate_pdf_report(
        self,
        apartments: List[ApartmentListing],
        filename: str = "investment_summary.pdf",
    ) -> str:
        """
        Generate complete PDF report with summary and apartment details.

        Args:
            apartments: List of apartments (already sorted by score)
            filename: Output filename

        Returns:
            Path to generated PDF file
        """
        if not apartments:
            raise ValueError("No apartments to generate PDF report")

        # Pre-create links and assign them to page numbers
        for idx, apt in enumerate(apartments, 1):
            link_id = self.pdf.add_link()
            page_num = idx + 1  # Page 1 is summary, apartments start at page 2
            self.pdf.set_link(link_id, page=page_num)
            self.apartment_links[apt.listing_id] = link_id

        # Generate pages
        self._add_summary_page(apartments)

        for idx, apt in enumerate(apartments, 1):
            self._add_apartment_detail_page(apt, idx, len(apartments))

        # Save PDF
        output_path = self.output_dir / filename
        self.pdf.output(str(output_path))

        return str(output_path)

    def _add_summary_page(self, apartments: List[ApartmentListing]):
        """
        Generate first page with investment summary table.

        Args:
            apartments: List of top N apartments
        """
        self.pdf.add_page()

        # Header section
        self._draw_summary_header(apartments)

        # Statistics box
        self._draw_statistics_box(apartments)

        # Investment ranking table
        self._draw_summary_table(apartments)

        # Footer
        self._add_page_footer(page_num=1, total_pages=len(apartments) + 1)

    def _draw_summary_header(self, apartments: List[ApartmentListing]):
        """Draw summary page header with run metadata."""
        # Title
        self.pdf.set_font("NotoSans", "B", 24)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(0, 15, "Immobilien Investment Bericht", ln=True, align="C")

        # Subtitle with timestamp
        self.pdf.set_font("NotoSans", "", 10)
        self.pdf.set_text_color(*self.GRAY)
        timestamp_str = self.run_timestamp.strftime("%d.%m.%Y %H:%M")
        self.pdf.cell(0, 6, f"Erstellt am {timestamp_str}", ln=True, align="C")

        self.pdf.ln(5)

        # Run metadata
        self.pdf.set_font("NotoSans", "", 9)
        self.pdf.set_text_color(0, 0, 0)

        # Portal
        portal = self.config.get("portal", "willhaben")
        self.pdf.cell(0, 5, f"Portal: {portal}", ln=True)

        # Postal codes
        postal_codes = self.config.get("postal_codes", [])
        if postal_codes:
            self.pdf.cell(0, 5, f"Postleitzahlen: {', '.join(postal_codes)}", ln=True)

        # Price filter
        price_max = self.config.get("price_max")
        if price_max:
            self.pdf.cell(0, 5, f"Max. Preis: €{price_max:,}", ln=True)

        self.pdf.ln(3)

    def _draw_statistics_box(self, apartments: List[ApartmentListing]):
        """Draw statistics box with counts."""
        y_start = self.pdf.get_y()

        # Background box
        self.pdf.set_fill_color(*self.LIGHT_GRAY)
        self.pdf.rect(10, y_start, 190, 20, "F")

        # Statistics
        self.pdf.set_font("NotoSans", "B", 10)
        self.pdf.set_y(y_start + 3)

        # Total apartments in summary
        col_width = 63.33
        self.pdf.set_x(10)
        self.pdf.cell(col_width, 7, f"Anzahl Wohnungen: {len(apartments)}", align="C")

        # Average score
        avg_score = sum(apt.investment_score or 0 for apt in apartments) / len(
            apartments
        )
        self.pdf.cell(
            col_width, 7, f"Durchschn. Bewertung: {avg_score:.1f}/10", align="C"
        )

        # Average yield
        yields = [apt.gross_yield for apt in apartments if apt.gross_yield]
        avg_yield = sum(yields) / len(yields) if yields else 0
        self.pdf.cell(col_width, 7, f"Durchschn. Rendite: {avg_yield:.1f}%", align="C")

        self.pdf.ln(15)

    def _draw_summary_table(self, apartments: List[ApartmentListing]):
        """Draw investment ranking table with clickable links."""
        self.pdf.ln(5)

        # Table header
        self.pdf.set_font("NotoSans", "B", 9)
        self.pdf.set_fill_color(*self.NAVY)
        self.pdf.set_text_color(*self.WHITE)

        # Column widths
        col_widths = {
            "rang": 12,
            "score": 18,
            "empfehlung": 30,
            "preis": 22,
            "groesse": 18,
            "rendite": 18,
            "lage": 42,
            "details": 20,
        }

        # Header row
        headers = [
            ("Rang", col_widths["rang"]),
            ("Bewertung", col_widths["score"]),
            ("Empfehlung", col_widths["empfehlung"]),
            ("Preis", col_widths["preis"]),
            ("Größe", col_widths["groesse"]),
            ("Rendite", col_widths["rendite"]),
            ("Lage", col_widths["lage"]),
            ("Details", col_widths["details"]),
        ]

        for header, width in headers:
            self.pdf.cell(width, 8, header, border=1, align="C", fill=True)

        self.pdf.ln()

        # Table rows
        self.pdf.set_font("NotoSans", "", 8)
        self.pdf.set_text_color(0, 0, 0)

        for idx, apt in enumerate(apartments, 1):
            # Check if we need a new page
            if self.pdf.get_y() > 250:
                self.pdf.add_page()
                # Redraw header
                self.pdf.set_font("NotoSans", "B", 9)
                self.pdf.set_fill_color(*self.NAVY)
                self.pdf.set_text_color(*self.WHITE)
                for header, width in headers:
                    self.pdf.cell(width, 8, header, border=1, align="C", fill=True)
                self.pdf.ln()
                self.pdf.set_font("NotoSans", "", 8)
                self.pdf.set_text_color(0, 0, 0)

            # Alternating row colors
            if idx % 2 == 0:
                self.pdf.set_fill_color(*self.LIGHT_GRAY)
                fill = True
            else:
                fill = False

            # Rang
            self.pdf.cell(
                col_widths["rang"], 7, str(idx), border=1, align="C", fill=fill
            )

            # Score with color coding
            score = apt.investment_score or 0
            score_color = self._get_score_color(score)
            self.pdf.set_text_color(*score_color)
            self.pdf.cell(
                col_widths["score"],
                7,
                f"{score:.1f}/10",
                border=1,
                align="C",
                fill=fill,
            )
            self.pdf.set_text_color(0, 0, 0)

            # Recommendation
            recommendation = apt.recommendation or PHRASES["n/a"]
            self.pdf.cell(
                col_widths["empfehlung"],
                7,
                recommendation[:18],
                border=1,
                align="C",
                fill=fill,
            )

            # Price
            price_str = f"€{apt.price:,.0f}" if apt.price else PHRASES["n/a"]
            self.pdf.cell(
                col_widths["preis"], 7, price_str, border=1, align="R", fill=fill
            )

            # Size
            size_str = f"{apt.size_sqm:.0f}m²" if apt.size_sqm else PHRASES["n/a"]
            self.pdf.cell(
                col_widths["groesse"], 7, size_str, border=1, align="C", fill=fill
            )

            # Yield
            yield_str = f"{apt.gross_yield:.1f}%" if apt.gross_yield else PHRASES["n/a"]
            self.pdf.cell(
                col_widths["rendite"], 7, yield_str, border=1, align="C", fill=fill
            )

            # Location
            location = self._format_location(apt)
            self.pdf.cell(
                col_widths["lage"], 7, location[:25], border=1, align="L", fill=fill
            )

            # Details link (clickable)
            self.pdf.set_text_color(*self.NAVY)
            self.pdf.set_font("NotoSans", "B", 8)
            link_id = self.apartment_links[apt.listing_id]
            self.pdf.cell(
                col_widths["details"],
                7,
                "Seite >",
                border=1,
                align="C",
                fill=fill,
                link=link_id,
            )
            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(0, 0, 0)

            self.pdf.ln()

    def _add_apartment_detail_page(self, apt: ApartmentListing, rank: int, total: int):
        """
        Generate detail page for one apartment with two-column layout.

        Args:
            apt: Apartment listing
            rank: Rank in investment ranking
            total: Total number of apartments
        """
        self.pdf.add_page()

        # Page header with title and score badge
        self._draw_apartment_header(apt, rank)

        # Two-column layout
        self._draw_two_column_layout(apt)

        # Data quality warnings (if present)
        self._draw_data_quality_warnings(apt)

        # Investment analysis section (full width)
        self._draw_investment_analysis(apt)

        # Footer with source link
        self._draw_apartment_footer(apt)

        # Page number
        self._add_page_footer(page_num=rank + 1, total_pages=total + 1)

    def _draw_apartment_header(self, apt: ApartmentListing, rank: int):
        """Draw apartment detail page header."""
        y_start = self.pdf.get_y()

        # Background bar
        self.pdf.set_fill_color(*self.NAVY)
        self.pdf.rect(10, y_start, 190, 20, "F")

        # Title - using custom format [size]-[price]-[location]-[ranking]
        self.pdf.set_y(y_start + 3)
        self.pdf.set_x(15)
        self.pdf.set_font("NotoSans", "B", 14)
        self.pdf.set_text_color(*self.WHITE)
        title = self._format_custom_title(apt, rank)
        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."
        self.pdf.cell(140, 7, title, ln=False)

        # Score badge (right side)
        score = apt.investment_score or 0
        score_color = self._get_score_color(score)

        # Badge background
        badge_x = 160
        self.pdf.set_fill_color(*score_color)
        self.pdf.rect(badge_x, y_start + 2, 35, 16, "F")

        # Badge text
        self.pdf.set_xy(badge_x, y_start + 5)
        self.pdf.set_font("NotoSans", "B", 12)
        self.pdf.set_text_color(*self.WHITE)
        self.pdf.cell(35, 7, f"{score:.1f}/10", align="C")

        # Rank subtitle
        self.pdf.set_xy(15, y_start + 11)
        self.pdf.set_font("NotoSans", "", 8)
        self.pdf.set_text_color(*self.LIGHT_GRAY)
        self.pdf.cell(0, 5, f"Rang #{rank}", ln=False)

        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_y(y_start + 22)

    def _draw_two_column_layout(self, apt: ApartmentListing):
        """Draw two-column layout with financial and property details."""
        y_start = self.pdf.get_y()
        col_width = 90
        gap = 10

        # Left column: Financial Analysis
        self.pdf.set_xy(10, y_start)
        self._draw_financial_column(apt, col_width)

        # Right column: Property Details
        self.pdf.set_xy(10 + col_width + gap, y_start)
        self._draw_property_column(apt, col_width)

        # Move cursor below both columns
        self.pdf.set_y(max(self.pdf.get_y(), y_start + 120))

    def _draw_financial_column(self, apt: ApartmentListing, width: float):
        """Draw left column with financial metrics."""
        x_start = self.pdf.get_x()
        y_start = self.pdf.get_y()

        # Section header
        self.pdf.set_font("NotoSans", "B", 11)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(width, 7, HEADERS["financial_analysis"], ln=True)

        self.pdf.set_font("NotoSans", "", 9)
        self.pdf.set_text_color(0, 0, 0)

        # Financial data
        financial_items = [
            (LABELS["price"], f"€{apt.price:,.0f}" if apt.price else PHRASES["n/a"]),
            (
                LABELS["price_per_sqm"],
                f"€{apt.price_per_sqm:,.0f}/m²"
                if apt.price_per_sqm
                else PHRASES["n/a"],
            ),
            (
                LABELS["betriebskosten_monthly"],
                f"€{apt.betriebskosten_monthly:,.0f}/Monat"
                if apt.betriebskosten_monthly
                else PHRASES["n/a"],
            ),
            (
                LABELS["estimated_rent"],
                f"€{apt.estimated_rent:,.0f}/Monat"
                if apt.estimated_rent
                else PHRASES["n/a"],
            ),
            (
                LABELS["gross_yield"],
                f"{apt.gross_yield:.1f}%" if apt.gross_yield else PHRASES["n/a"],
            ),
            (
                LABELS["net_yield"],
                f"{apt.net_yield:.1f}%" if apt.net_yield else PHRASES["n/a"],
            ),
            (
                LABELS["cash_flow_monthly"],
                self._format_cash_flow(apt.cash_flow_monthly),
            ),
        ]

        for label, value in financial_items:
            self.pdf.set_x(x_start)
            # Label
            self.pdf.set_font("NotoSans", "B", 8)
            self.pdf.set_text_color(*self.GRAY)
            self.pdf.cell(width * 0.5, 5, label + ":", ln=False)
            # Value
            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(width * 0.5, 5, value, ln=True)

        # Recommendation badge
        self.pdf.ln(3)
        self.pdf.set_x(x_start)
        self.pdf.set_font("NotoSans", "B", 9)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(width, 5, LABELS["recommendation"] + ":", ln=True)

        self.pdf.set_x(x_start)
        recommendation = apt.recommendation or PHRASES["n/a"]
        self.pdf.set_font("NotoSans", "B", 10)
        score_color = self._get_score_color(apt.investment_score or 0)
        self.pdf.set_text_color(*score_color)
        self.pdf.cell(width, 6, recommendation, ln=True)

        self.pdf.set_text_color(0, 0, 0)

    def _draw_property_column(self, apt: ApartmentListing, width: float):
        """Draw right column with property details."""
        x_start = self.pdf.get_x()
        y_start = self.pdf.get_y()

        # Section header
        self.pdf.set_font("NotoSans", "B", 11)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(width, 7, HEADERS["property_details"], ln=True)

        self.pdf.set_font("NotoSans", "", 9)
        self.pdf.set_text_color(0, 0, 0)

        # Property specs
        property_items = [
            (
                LABELS["size_sqm"],
                f"{apt.size_sqm:.0f}m²" if apt.size_sqm else PHRASES["n/a"],
            ),
            (LABELS["rooms"], str(apt.rooms) if apt.rooms else PHRASES["n/a"]),
            (
                LABELS["floor"],
                apt.floor_text or str(apt.floor) if apt.floor else PHRASES["n/a"],
            ),
            (LABELS["condition"], apt.condition or PHRASES["n/a"]),
            (
                LABELS["year_built"],
                str(apt.year_built) if apt.year_built else PHRASES["n/a"],
            ),
            (LABELS["building_type"], apt.building_type or PHRASES["n/a"]),
        ]

        for label, value in property_items:
            self.pdf.set_x(x_start)
            # Label
            self.pdf.set_font("NotoSans", "B", 8)
            self.pdf.set_text_color(*self.GRAY)
            self.pdf.cell(width * 0.5, 5, label + ":", ln=False)
            # Value
            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.cell(width * 0.5, 5, value, ln=True)

        # Features section
        self.pdf.ln(3)
        self.pdf.set_x(x_start)
        self.pdf.set_font("NotoSans", "B", 9)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(width, 5, HEADERS["features"] + ":", ln=True)

        features = []
        if apt.elevator:
            features.append("Aufzug")
        if apt.balcony:
            features.append("Balkon")
        if apt.terrace:
            features.append("Terrasse")
        if apt.parking:
            features.append("Parkplatz")
        if apt.cellar:
            features.append("Keller")
        if apt.garden:
            features.append("Garten")

        self.pdf.set_x(x_start)
        self.pdf.set_font("NotoSans", "", 8)
        self.pdf.set_text_color(0, 0, 0)
        features_text = ", ".join(features) if features else "Keine"
        self.pdf.multi_cell(width, 4, features_text)

        # Location
        self.pdf.ln(2)
        self.pdf.set_x(x_start)
        self.pdf.set_font("NotoSans", "B", 9)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(width, 5, HEADERS["location"] + ":", ln=True)

        location = self._format_full_location(apt)
        self.pdf.set_x(x_start)
        self.pdf.set_font("NotoSans", "", 8)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.multi_cell(width, 4, location)

        self.pdf.set_text_color(0, 0, 0)

    def _draw_data_quality_warnings(self, apt: ApartmentListing):
        """Draw data quality warnings section if present."""
        if not apt.data_quality_warnings:
            return

        # Check if we need a new page
        if self.pdf.get_y() > 250:
            self.pdf.add_page()

        self.pdf.ln(5)

        # Section header
        self.pdf.set_font("NotoSans", "B", 10)
        self.pdf.set_text_color(*self.COLOR_POOR)  # Red for warnings
        self.pdf.cell(0, 6, "Datenqualitaet-Hinweise", ln=True)

        # Warnings
        self.pdf.set_font("NotoSans", "", 9)
        self.pdf.set_text_color(0, 0, 0)
        for warning in apt.data_quality_warnings:
            # Use simple bullet and proper margins
            x_start = self.pdf.get_x()
            self.pdf.cell(5, 5, "-", ln=False)
            self.pdf.set_x(x_start + 5)

            # Multi-cell with proper width (page width - margins - bullet indent)
            # Page width is 210mm, margins are 10mm on each side, bullet indent is 5mm
            available_width = 210 - 10 - 10 - 5
            self.pdf.multi_cell(available_width, 5, warning)

        self.pdf.ln(3)
        self.pdf.set_text_color(0, 0, 0)  # Reset to black

    def _draw_investment_analysis(self, apt: ApartmentListing):
        """Draw full-width investment analysis section."""
        if not apt.positive_factors and not apt.risk_factors:
            return

        self.pdf.ln(5)

        # Section header
        self.pdf.set_font("NotoSans", "B", 11)
        self.pdf.set_text_color(*self.NAVY)
        self.pdf.cell(0, 7, HEADERS["investment_analysis"], ln=True)

        # Positive factors
        if apt.positive_factors:
            self.pdf.set_font("NotoSans", "B", 9)
            self.pdf.set_text_color(40, 167, 69)  # Green
            self.pdf.cell(0, 5, "+ Positive Faktoren:", ln=True)

            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(0, 0, 0)
            for factor in apt.positive_factors[:5]:  # Limit to 5
                self.pdf.set_x(15)  # Set absolute x position for indent
                self.pdf.multi_cell(185, 4, f"• {factor}")

        # Risk factors
        if apt.risk_factors:
            self.pdf.ln(2)
            self.pdf.set_font("NotoSans", "B", 9)
            self.pdf.set_text_color(220, 53, 69)  # Red
            self.pdf.cell(0, 5, "! Risikofaktoren:", ln=True)

            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(0, 0, 0)
            for factor in apt.risk_factors[:5]:  # Limit to 5
                self.pdf.set_x(15)  # Set absolute x position for indent
                self.pdf.multi_cell(185, 4, f"• {factor}")

        # LLM Summary section (if available)
        if apt.llm_summary:
            self.pdf.ln(4)

            # Section header
            self.pdf.set_font("NotoSans", "B", 9)
            self.pdf.set_text_color(*self.NAVY)
            self.pdf.cell(0, 5, HEADERS["llm_summary_section"], ln=True)

            # Summary text
            self.pdf.set_font("NotoSans", "", 8)
            self.pdf.set_text_color(*self.GRAY)
            self.pdf.multi_cell(185, 4, apt.llm_summary)

        self.pdf.set_text_color(0, 0, 0)

    def _draw_apartment_footer(self, apt: ApartmentListing):
        """Draw apartment footer with source link."""
        # Position near bottom
        self.pdf.set_y(270)

        # Divider line
        self.pdf.set_draw_color(*self.GRAY)
        self.pdf.line(10, 270, 200, 270)

        # Source URL
        self.pdf.set_font("NotoSans", "", 7)
        self.pdf.set_text_color(*self.GRAY)
        self.pdf.cell(0, 4, "Quelle:", ln=True)

        self.pdf.set_font("NotoSans", "", 7)
        self.pdf.set_text_color(*self.NAVY)
        if apt.source_url:
            # Make URL clickable
            self.pdf.cell(0, 4, apt.source_url, ln=True, link=apt.source_url)
        else:
            self.pdf.cell(0, 4, PHRASES["n/a"], ln=True)

        self.pdf.set_text_color(0, 0, 0)

    def _add_page_footer(self, page_num: int, total_pages: int):
        """Add page number footer."""
        self.pdf.set_y(285)
        self.pdf.set_font("NotoSans", "", 8)
        self.pdf.set_text_color(*self.GRAY)
        self.pdf.cell(0, 5, f"Seite {page_num} von {total_pages}", align="C")
        self.pdf.set_text_color(0, 0, 0)

    def _get_score_color(self, score: float) -> tuple:
        """Get color based on investment score."""
        if score >= 8.0:
            return self.COLOR_EXCELLENT  # Green
        elif score >= 6.5:
            return self.COLOR_GOOD  # Blue
        elif score >= 5.0:
            return self.COLOR_AVERAGE  # Yellow
        elif score >= 3.5:
            return self.COLOR_WEAK  # Orange
        else:
            return self.COLOR_POOR  # Red

    def _format_location(self, apt: ApartmentListing) -> str:
        """Format location string (city, district)."""
        parts = []

        if apt.city:
            parts.append(apt.city)

        if apt.district:
            parts.append(apt.district)
        elif apt.district_number:
            parts.append(f"Bez. {apt.district_number}")

        return ", ".join(parts) if parts else PHRASES["n/a"]

    def _format_full_location(self, apt: ApartmentListing) -> str:
        """Format full location with address."""
        parts = []

        if apt.street:
            parts.append(apt.street)

        if apt.postal_code and apt.city:
            parts.append(f"{apt.postal_code} {apt.city}")
        elif apt.city:
            parts.append(apt.city)

        if apt.district:
            parts.append(f"({apt.district})")

        return ", ".join(parts) if parts else PHRASES["n/a"]

    def _format_cash_flow(self, cash_flow: Optional[float]) -> str:
        """Format cash flow with color indication."""
        if cash_flow is None:
            return PHRASES["n/a"]

        if cash_flow >= 0:
            return f"€{cash_flow:,.0f}/Monat"
        else:
            return f"-€{abs(cash_flow):,.0f}/Monat"

    def _format_custom_title(self, apt: ApartmentListing, rank: int) -> str:
        """
        Format custom title as [size]-[price]-[location]-[ranking].
        Uses 'n.A.' for unavailable attributes.
        """
        # Size
        size_str = f"{apt.size_sqm:.0f}m²" if apt.size_sqm else "n.A."

        # Price
        price_str = f"€{apt.price:,.0f}" if apt.price else "n.A."

        # Location (city or city + district)
        location_parts = []
        if apt.city:
            location_parts.append(apt.city)
        if apt.district:
            location_parts.append(apt.district)
        elif apt.district_number:
            location_parts.append(f"Bez.{apt.district_number}")

        location_str = " ".join(location_parts) if location_parts else "n.A."

        # Ranking
        rank_str = f"#{rank}"

        # Combine with dashes
        return f"{size_str} - {price_str} - {location_str} - {rank_str}"
