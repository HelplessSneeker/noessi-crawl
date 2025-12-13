"""Enhanced apartment scraper with investment analysis."""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from crawl4ai import AsyncWebCrawler

from llm.analyzer import InvestmentAnalyzer
from llm.extractor import OllamaExtractor
from llm.summarizer import ApartmentSummarizer
from models.apartment import ApartmentListing
from models.constants import AREA_ID_TO_LOCATION, PLZ_TO_AREA_ID
from models.metadata import ApartmentMetadata
from utils.address_parser import AustrianAddressParser
from utils.extractors import AustrianRealEstateExtractor
from utils.markdown_generator import MarkdownGenerator
from utils.pdf_generator import PDFGenerator
from utils.top_n_tracker import TopNTracker
from utils.translations import HEADERS, LABELS, PHRASES, RECOMMENDATIONS, TABLE_HEADERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress font subsetting logs from PDF generation
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)


class EnhancedApartmentScraper:
    """Enhanced apartment scraper with investment analysis capabilities."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scraper with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.portal = config.get("portal", "willhaben")

        # Generate timestamped run folder
        self.run_timestamp = datetime.now()
        self.run_id = self.run_timestamp.strftime("%Y-%m-%d-%H%M%S")

        # Initialize components
        self.extractor = AustrianRealEstateExtractor()
        self.address_parser = AustrianAddressParser()

        # LLM extractor (optional)
        llm_config = config.get("llm_settings", {})
        self.use_llm = llm_config.get("enabled", False)

        if self.use_llm:
            llm_model = llm_config.get("model", "qwen3:8b")
            diagnostic_logging = llm_config.get("diagnostics_enabled", False)
            html_max_chars = llm_config.get("html_max_chars", 50000)
            self.llm_extractor = OllamaExtractor(
                model=llm_model,
                diagnostic_logging=diagnostic_logging,
                html_max_chars=html_max_chars
            )
        else:
            self.llm_extractor = None

        # Investment analyzer
        analysis_config = config.get("analysis", {})
        self.analyzer = InvestmentAnalyzer(analysis_config)

        # LLM summarizer (optional)
        self.generate_llm_summary = llm_config.get("generate_summary", False)
        if self.generate_llm_summary:
            llm_model = llm_config.get("model", "qwen3:8b")
            summary_max_words = llm_config.get("summary_max_words", 150)
            summary_timeout = llm_config.get("summary_timeout", 120)  # NEW: Get timeout from config
            summary_min_words = llm_config.get("summary_min_words", 80)  # NEW: Get min words from config
            self.summarizer = ApartmentSummarizer(
                model=llm_model,
                max_words=summary_max_words,
                timeout=summary_timeout,  # NEW: Pass timeout
                min_words=summary_min_words  # NEW: Pass min words
            )
        else:
            self.summarizer = None

        # Markdown generator with timestamped folder
        output_folder = config.get("output_folder", "output")
        self.run_folder = Path(output_folder) / f"apartments_{self.run_id}"
        self.md_generator = MarkdownGenerator(output_dir=str(self.run_folder))

        # Filters
        self.filters = config.get("filters", {})

        # Output settings
        output_config = config.get("output", {})
        self.include_rejected = output_config.get("include_rejected", False)
        self.generate_summary = output_config.get("generate_summary", True)
        # Support both old and new config field names
        self.pdf_top_n = output_config.get("pdf_top_n", output_config.get("summary_top_n", 20))

        # Rate limiting
        rate_config = config.get("rate_limiting", {})
        self.delay_apartment = rate_config.get("delay_apartment", 0.5)
        self.delay_page = rate_config.get("delay_page", 1.0)

        # Tracking - NEW: lightweight metadata instead of full objects
        self.seen_listings: Set[str] = set()
        self.apartment_metadata: List[ApartmentMetadata] = []
        self.top_n_tracker = TopNTracker(self.pdf_top_n)

        # Create apartments subfolder immediately
        self.apartments_folder = self.run_folder / "apartments"
        self.apartments_folder.mkdir(parents=True, exist_ok=True)

        # Translate postal codes to area_ids for willhaben
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

    def build_willhaben_url(self, page: int = 1) -> str:
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

    async def extract_apartment_data(
        self, html: str, url: str
    ) -> Optional[ApartmentListing]:
        """
        Extract apartment data using multi-strategy approach.

        1. JSON-LD structured data (primary)
        2. Regex patterns (fallback)
        3. LLM extraction (if enabled, for missing fields)
        """
        listing_id = self.extract_listing_id(url)

        # Check for ad filtering - star icon indicates real listing
        star_icon_path = "m12 4 2.09 4.25a1.52 1.52 0 0 0 1.14.82l4.64.64-3.42 3.32"
        if star_icon_path not in html:
            logger.debug(f"Skipping ad/promoted listing: {url}")
            return None

        # Initialize apartment with basic data
        apartment = ApartmentListing(
            listing_id=listing_id,
            source_url=url,
            source_portal=self.portal,
        )

        # Strategy 1: Extract from JSON-LD
        json_ld_data = self._extract_json_ld(html)
        if json_ld_data:
            apartment.raw_json_ld = json_ld_data
            self._apply_json_ld_data(apartment, json_ld_data)

        # Strategy 1.5: DOM-based extraction (more reliable for separated labels/values)
        dom_data = self.extractor.extract_from_html_dom(html)
        if dom_data:
            self._apply_regex_data(apartment, dom_data)  # Reuse same apply logic
            logger.debug(f"DOM extraction found {len(dom_data)} fields")

        # Strategy 2: Extract using regex patterns (more authoritative for betriebskosten)
        regex_data = self.extractor.extract_from_html(html)

        # Diagnostic logging for critical fields
        if "size_sqm" in regex_data:
            logger.info(
                f"Regex extracted size_sqm: {regex_data['size_sqm']} m² "
                f"for {url}"
            )

        self._apply_regex_data(apartment, regex_data, allow_betriebskosten_overwrite=True)

        # Extract address
        address_text = self._extract_address_from_html(html, url)
        if address_text:
            parsed_address = self.address_parser.parse_address(address_text)
            self._apply_address_data(apartment, parsed_address)

        # Strategy 3: LLM extraction (if enabled and quality-based triggers)
        llm_data = None  # Initialize to prevent UnboundLocalError in diagnostics
        if self.use_llm and self.llm_extractor:
            # Get trigger configuration
            trigger_mode = self.config.get("llm_settings", {}).get("trigger_mode", "conservative")
            quality_check = self.config.get("llm_settings", {}).get("quality_check_enabled", True)

            should_run_llm = False
            trigger_reason = []

            # Check 1: Critical fields missing (original logic)
            missing_critical = not apartment.price or not apartment.size_sqm
            if missing_critical:
                should_run_llm = True
                trigger_reason.append("missing_critical_fields")

            # Check 2: Quality issues (NEW - aggressive mode)
            if quality_check and not missing_critical:
                quality_issues = self._detect_quality_issues(apartment)
                if quality_issues:
                    should_run_llm = True
                    trigger_reason.extend(quality_issues)

            # Check 3: Missing important fields
            if trigger_mode in ["aggressive", "always"]:
                if self._has_missing_fields(apartment):
                    should_run_llm = True
                    if "missing_optional_fields" not in trigger_reason:
                        trigger_reason.append("missing_optional_fields")

            # Check 4: Always run (for testing)
            if trigger_mode == "always":
                should_run_llm = True
                if "always_mode" not in trigger_reason:
                    trigger_reason.append("always_mode")

            if should_run_llm:
                # Count non-None fields before LLM extraction
                import time
                fields_before = sum(1 for k, v in apartment.to_dict().items() if v not in (None, ""))
                start_time = time.time()

                logger.info(
                    f"LLM extraction triggered for {listing_id}: {', '.join(trigger_reason)} "
                    f"(fields before: {fields_before})"
                )
                existing_data = apartment.to_dict()
                try:
                    # Add hard timeout wrapper to prevent indefinite hangs
                    extraction_timeout = self.config.get("llm_settings", {}).get("extraction_timeout", 180)
                    llm_data = await asyncio.wait_for(
                        self.llm_extractor.extract_structured_data(html, existing_data),
                        timeout=extraction_timeout,
                    )
                    logger.info(f"LLM extraction completed for listing {listing_id}")
                    self._apply_llm_data(apartment, llm_data)

                    # Count non-None fields after LLM extraction
                    fields_after = sum(1 for k, v in apartment.to_dict().items() if v not in (None, ""))
                    elapsed_time = time.time() - start_time
                    fields_added = fields_after - fields_before

                    if fields_added > 0:
                        logger.info(
                            f"LLM extraction added {fields_added} fields "
                            f"(before: {fields_before} → after: {fields_after}) "
                            f"in {elapsed_time:.1f}s"
                        )
                    else:
                        logger.warning(
                            f"LLM extraction completed but added 0 new fields in {elapsed_time:.1f}s"
                        )

                except asyncio.TimeoutError:
                    logger.error(
                        f"LLM extraction timed out after {extraction_timeout}s for listing {listing_id}, "
                        f"continuing without LLM data"
                    )
                except Exception as e:
                    logger.error(f"LLM extraction failed for listing {listing_id}: {e}")
            else:
                logger.debug(
                    f"Skipping LLM extraction for {listing_id} - no quality issues detected"
                )

        # Extract title from markdown/HTML if not set
        if not apartment.title:
            apartment.title = self._extract_title(html)

        # Enrich location data from area_ids if missing
        self._enrich_location_from_area_ids(apartment)

        # Note: Validation now happens in process_apartment() to allow saving invalid apartments
        # with validation_failed flag for manual review

        # Diagnostic mode: save extraction data for debugging
        if self.config.get("llm_settings", {}).get("diagnostics_enabled", False):
            self._save_diagnostic_data(
                listing_id=listing_id,
                url=url,
                html=html,
                json_ld_data=json_ld_data,
                regex_data=regex_data,
                llm_data=llm_data if self.use_llm else None,
                apartment=apartment
            )

        return apartment

    def _extract_json_ld(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD product data from HTML."""
        try:
            # Look for product JSON-LD
            match = re.search(
                r'<script type="application/ld\+json">({.*?"@type":\s*"Product".*?})</script>',
                html,
                re.DOTALL,
            )
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            logger.debug(f"Error parsing JSON-LD: {e}")
        return None

    def _apply_json_ld_data(
        self, apartment: ApartmentListing, data: Dict[str, Any]
    ) -> None:
        """Apply JSON-LD data to apartment."""
        if "name" in data:
            apartment.title = data["name"]

        # Price from offers
        offers = data.get("offers", {})
        if isinstance(offers, dict):
            price = offers.get("price")
            if price:
                try:
                    apartment.price = float(price)
                except (ValueError, TypeError):
                    pass

            # Extract address from nested structure: offers > availableAtOrFrom > address
            available_at = offers.get("availableAtOrFrom", {})
            if isinstance(available_at, dict):
                address = available_at.get("address", {})
                if isinstance(address, dict):
                    # Extract structured address fields
                    if address.get("postalCode") and not apartment.postal_code:
                        apartment.postal_code = str(address["postalCode"])
                        logger.debug(f"Extracted postal_code from JSON-LD: {apartment.postal_code}")

                    if address.get("addressLocality") and not apartment.city:
                        apartment.city = str(address["addressLocality"])
                        logger.debug(f"Extracted city from JSON-LD: {apartment.city}")

                    if address.get("streetAddress") and not apartment.street:
                        street_text = str(address["streetAddress"])
                        # Parse street and house number
                        street_match = re.match(r"^(.+?)\s+(\d+[a-zA-Z]?)$", street_text)
                        if street_match:
                            apartment.street = street_match.group(1).strip()
                            apartment.house_number = street_match.group(2)
                            logger.debug(f"Extracted street from JSON-LD: {apartment.street} {apartment.house_number}")
                        else:
                            apartment.street = street_text
                            logger.debug(f"Extracted street from JSON-LD: {apartment.street}")

                    if address.get("addressRegion") and not apartment.state:
                        apartment.state = str(address["addressRegion"])

                    # Vienna district extraction from postal code
                    if apartment.postal_code and apartment.postal_code.startswith("1"):
                        district_num = self.address_parser.extract_district_from_text(apartment.postal_code)
                        if district_num and not apartment.district_number:
                            apartment.district_number = district_num
                            from models.constants import VIENNA_DISTRICTS
                            apartment.district = VIENNA_DISTRICTS.get(district_num, {}).get("name")
                            logger.debug(f"Extracted Vienna district from JSON-LD postal code: {district_num}")

    def _apply_regex_data(
        self, apartment: ApartmentListing, data: Dict[str, Any], allow_betriebskosten_overwrite: bool = False
    ) -> None:
        """Apply regex-extracted data to apartment."""
        # Only apply if not already set
        if not apartment.price and "price" in data:
            apartment.price = data["price"]
        if not apartment.size_sqm and "size_sqm" in data:
            apartment.size_sqm = data["size_sqm"]
        if not apartment.rooms and "rooms" in data:
            apartment.rooms = data["rooms"]

        # Special handling for betriebskosten: allow regex to overwrite DOM extraction
        if allow_betriebskosten_overwrite and "betriebskosten_monthly" in data:
            new_value = data["betriebskosten_monthly"]
            current_value = apartment.betriebskosten_monthly
            # Only overwrite if regex found a value (don't overwrite with None)
            if new_value is not None:
                if current_value and current_value != new_value:
                    logger.info(
                        f"Regex overwriting betriebskosten: €{current_value} → €{new_value} "
                        f"(regex patterns are more authoritative)"
                    )
                apartment.betriebskosten_monthly = new_value

        # Apply other fields
        field_mappings = [
            "betriebskosten_monthly",  # Will be skipped if already applied above
            "reparaturrucklage",
            "floor",
            "floor_text",
            "year_built",
            "condition",
            "building_type",
            "energy_rating",
            "hwb_value",
            "fgee_value",
            "heating_type",
            "elevator",
            "balcony",
            "terrace",
            "garden",
            "parking",
            "cellar",
            "storage",
            "commission_free",
            "commission_percent",
        ]

        for field in field_mappings:
            if field in data and getattr(apartment, field) is None:
                setattr(apartment, field, data[field])

    def _apply_address_data(
        self, apartment: ApartmentListing, data: Dict[str, Any]
    ) -> None:
        """Apply parsed address data to apartment."""
        if data.get("street"):
            apartment.street = data["street"]
        if data.get("house_number"):
            apartment.house_number = data["house_number"]
        if data.get("door_number"):
            apartment.door_number = data["door_number"]
        if data.get("postal_code"):
            apartment.postal_code = data["postal_code"]
        if data.get("city"):
            apartment.city = data["city"]
        if data.get("district"):
            apartment.district = data["district"]
        if data.get("district_number"):
            apartment.district_number = data["district_number"]
        if data.get("state"):
            apartment.state = data["state"]
        if data.get("full_address"):
            apartment.full_address = data["full_address"]

    def _enrich_location_from_area_ids(self, apartment: ApartmentListing) -> None:
        """Enrich missing location data using area_id to location mapping."""
        # DISABLED: This method was causing incorrect location enrichment
        # where apartments in Villach/Klagenfurt were being tagged as "1010 Wien"
        # because that was in the configured postal_codes list.
        #
        # We now rely solely on extracted address data from the listing HTML.
        pass

    def _validate_critical_fields(self, apartment: ApartmentListing) -> tuple[bool, Optional[str]]:
        """
        Validate that critical fields are present for investment analysis.

        Critical fields:
        - price: Must have a purchase price
        - size_sqm: Must know apartment size for per-sqm calculations
        - betriebskosten_monthly: Essential for cash flow and yield analysis

        Returns:
            (is_valid, rejection_reason)
            - (True, None) if all critical fields present
            - (False, "reason") if any critical field missing
        """
        missing_fields = []

        # Check price
        if not apartment.price or apartment.price <= 0:
            missing_fields.append("price")
            logger.warning(f"Validation failed for {apartment.listing_id}: price={apartment.price}")

        # Check size - must be at least 10 m² (reject extraction errors)
        if not apartment.size_sqm or apartment.size_sqm < 10.0:
            missing_fields.append("size_sqm")
            logger.warning(
                f"Validation failed for {apartment.listing_id}: size_sqm={apartment.size_sqm} "
                f"(minimum 10 m² required)"
            )

        # Check operating costs
        if not apartment.betriebskosten_monthly or apartment.betriebskosten_monthly <= 0:
            missing_fields.append("betriebskosten_monthly")
            logger.warning(
                f"Validation failed for {apartment.listing_id}: "
                f"betriebskosten_monthly={apartment.betriebskosten_monthly}"
            )

        if missing_fields:
            reason = f"Missing critical fields: {', '.join(missing_fields)}"
            logger.warning(f"VALIDATION FAILED for {apartment.listing_id}: {reason}")
            return (False, reason)

        logger.info(f"Validation passed for {apartment.listing_id}")
        return (True, None)

    def _detect_quality_issues(self, apartment: ApartmentListing) -> List[str]:
        """
        Detect suspicious/invalid extracted values that should trigger LLM re-extraction.

        Returns:
            List of quality issue descriptions (empty if no issues)
        """
        issues = []

        # Financial field quality checks (CRITICAL)
        if apartment.betriebskosten_monthly:
            if apartment.betriebskosten_monthly < 30:
                issues.append(f"betriebskosten_suspicious(€{apartment.betriebskosten_monthly}<€30)")
            if apartment.size_sqm and apartment.betriebskosten_monthly / apartment.size_sqm < 0.5:
                issues.append(f"betriebskosten_per_sqm_too_low(€{apartment.betriebskosten_monthly/apartment.size_sqm:.2f}/m²)")
        else:
            issues.append("betriebskosten_missing")

        if apartment.reparaturrucklage and apartment.reparaturrucklage < 10:
            issues.append(f"reparaturrucklage_suspicious(€{apartment.reparaturrucklage}<€10)")

        # Bedroom/bathroom sanity checks
        if apartment.bedrooms == 0 and apartment.rooms and apartment.rooms >= 1.5:
            issues.append(f"bedrooms_zero_but_rooms={apartment.rooms}")

        if apartment.bathrooms == 0 and apartment.size_sqm and apartment.size_sqm > 25:
            issues.append("bathrooms_zero_unlikely")

        # Floor validation
        if apartment.floor and apartment.floor > 20:
            issues.append(f"floor_unlikely({apartment.floor}>20)")

        # Year built sanity
        if apartment.year_built and (apartment.year_built < 1700 or apartment.year_built > 2030):
            issues.append(f"year_built_invalid({apartment.year_built})")

        # HWB value sanity (typical: 20-300 kWh/m²a)
        if apartment.hwb_value:
            if apartment.hwb_value > 1000:
                issues.append(f"hwb_value_unrealistic({apartment.hwb_value}>1000)")
            if apartment.hwb_value < 5 and apartment.hwb_value > 0:
                issues.append(f"hwb_value_too_low({apartment.hwb_value}<5)")

        return issues

    def _apply_llm_data(
        self, apartment: ApartmentListing, data: Dict[str, Any]
    ) -> None:
        """
        Apply LLM-extracted data to apartment with smart overwrite logic.

        Strategy:
        - Fill missing fields (always)
        - Replace suspicious/invalid values (quality-based)
        - Log all replacements for debugging
        """
        fields_added = []
        fields_replaced = []
        fields_kept = []

        # Helper function for overwrite decisions
        def should_overwrite(field_name: str, current_value: Any, llm_value: Any) -> tuple[bool, str]:
            """Returns (should_overwrite, reason)"""
            if current_value is None or current_value == "":
                return (True, "missing")

            # Financial fields with quality checks
            if field_name == "betriebskosten_monthly":
                if current_value < 30:  # Unrealistically low
                    return (True, f"too_low(€{current_value}<€30)")
                if llm_value and llm_value > 30 and llm_value > current_value * 5:
                    return (True, f"llm_much_higher(€{current_value}→€{llm_value})")
                return (False, f"reasonable(€{current_value})")

            if field_name == "reparaturrucklage":
                if current_value < 10:
                    return (True, f"too_low(€{current_value}<€10)")
                if llm_value and llm_value > 10 and llm_value > current_value * 3:
                    return (True, f"llm_much_higher(€{current_value}→€{llm_value})")
                return (False, f"reasonable(€{current_value})")

            # Bedroom/bathroom zero checks
            if field_name == "bedrooms":
                if current_value == 0 and llm_value and llm_value > 0:
                    return (True, "zero_replaced")
                return (False, f"keep({current_value})")

            if field_name == "bathrooms":
                if current_value == 0 and llm_value and llm_value > 0:
                    return (True, "zero_replaced")
                return (False, f"keep({current_value})")

            # Floor validation
            if field_name == "floor":
                if current_value > 20 or current_value < -2:
                    return (True, f"unlikely({current_value})")
                return (False, f"keep({current_value})")

            # Year built validation
            if field_name == "year_built":
                if current_value < 1700 or current_value > 2030:
                    return (True, f"invalid({current_value})")
                return (False, f"keep({current_value})")

            # HWB value validation
            if field_name == "hwb_value":
                if current_value > 1000 or (current_value < 5 and current_value > 0):
                    return (True, f"unrealistic({current_value})")
                return (False, f"keep({current_value})")

            return (False, "exists")

        # Apply each field with smart overwrite logic
        field_mappings = {
            "title": "title",
            "price": "price",
            "size_sqm": "size_sqm",
            "rooms": "rooms",
            "bedrooms": "bedrooms",
            "bathrooms": "bathrooms",
            "floor": "floor",
            "year_built": "year_built",
            "condition": "condition",
            "building_type": "building_type",
            "energy_rating": "energy_rating",
            "heating_type": "heating_type",
            "betriebskosten_monthly": "betriebskosten_monthly",
            "reparaturrucklage": "reparaturrucklage",
            "hwb_value": "hwb_value",
        }

        for llm_key, apt_field in field_mappings.items():
            if llm_key not in data or data[llm_key] is None:
                continue

            llm_value = data[llm_key]
            current_value = getattr(apartment, apt_field)

            should_replace, reason = should_overwrite(apt_field, current_value, llm_value)

            if should_replace:
                setattr(apartment, apt_field, llm_value)
                if current_value is not None and current_value != "":
                    fields_replaced.append(f"{apt_field}={current_value}→{llm_value} ({reason})")
                else:
                    fields_added.append(f"{apt_field}={llm_value}")
            else:
                fields_kept.append(f"{apt_field}={current_value} ({reason})")

        # Boolean features (always fill if missing)
        boolean_fields = {
            "elevator": "elevator",
            "balcony": "balcony",
            "terrace": "terrace",
            "garden": "garden",
            "parking": "parking",
            "cellar": "cellar",
            "commission_free": "commission_free",
        }

        for llm_key, apt_field in boolean_fields.items():
            if llm_key in data and data[llm_key] is not None:
                current_value = getattr(apartment, apt_field)
                if current_value is None:
                    setattr(apartment, apt_field, data[llm_key])
                    fields_added.append(f"{apt_field}={data[llm_key]}")

        # Logging summary
        if fields_added:
            logger.info(f"LLM added {len(fields_added)} fields: {', '.join(fields_added[:10])}")
        if fields_replaced:
            logger.info(f"LLM replaced {len(fields_replaced)} suspicious values: {', '.join(fields_replaced)}")
        if fields_kept and self.config.get("llm_settings", {}).get("diagnostics_enabled"):
            logger.debug(f"LLM kept {len(fields_kept)} existing values")

        # Address from LLM
        if data.get("address") and not apartment.full_address:
            parsed = self.address_parser.parse_address(data["address"])
            self._apply_address_data(apartment, parsed)

    def _has_missing_fields(self, apartment: ApartmentListing) -> bool:
        """Check if apartment has important missing fields."""
        # Categorized by user priority: Financial > Features > Address

        # Financial fields (HIGHEST PRIORITY)
        financial_fields = [
            "betriebskosten_monthly",
            "reparaturrucklage",
            "heating_cost_monthly",
            "price_per_sqm",
        ]

        # Property features
        feature_fields = [
            "bedrooms",
            "bathrooms",
            "elevator",
            "balcony",
            "terrace",
            "garden",
            "parking",
            "cellar",
            "commission_free",
        ]

        # Address details
        address_fields = [
            "postal_code",
            "city",
            "street",
            "house_number",
            "district",
        ]

        # Other important fields
        other_fields = [
            "rooms",
            "year_built",
            "condition",
            "energy_rating",
            "hwb_value",
        ]

        # Check each category and log which triggered LLM
        missing_financial = [f for f in financial_fields if getattr(apartment, f) is None]
        missing_features = [f for f in feature_fields if getattr(apartment, f) is None]
        missing_address = [f for f in address_fields if getattr(apartment, f) is None]
        missing_other = [f for f in other_fields if getattr(apartment, f) is None]

        has_missing = bool(missing_financial or missing_features or missing_address or missing_other)

        if has_missing:
            categories = []
            if missing_financial:
                categories.append(f"financial({len(missing_financial)})")
            if missing_features:
                categories.append(f"features({len(missing_features)})")
            if missing_address:
                categories.append(f"address({len(missing_address)})")
            if missing_other:
                categories.append(f"other({len(missing_other)})")
            logger.info(f"LLM extraction triggered - missing: {', '.join(categories)}")

        return has_missing

    def _extract_address_from_html(self, html: str, url: str) -> Optional[str]:
        """Extract address from HTML or URL."""
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

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract title from HTML."""
        # Try h1 tag
        h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
        if h1_match:
            title = h1_match.group(1).strip()
            if len(title) > 5 and "cookie" not in title.lower():
                return title

        # Try og:title meta
        og_match = re.search(
            r'<meta property="og:title" content="([^"]+)"', html, re.IGNORECASE
        )
        if og_match:
            return og_match.group(1).strip()

        return None

    def _extract_metadata(
        self,
        apartment: ApartmentListing,
        filepath: str,
        validation_failed: bool,
        validation_reason: Optional[str]
    ) -> ApartmentMetadata:
        """
        Extract lightweight metadata from full apartment object.

        Args:
            apartment: Full apartment listing
            filepath: Absolute filepath where apartment was saved
            validation_failed: Whether validation failed
            validation_reason: Reason for validation failure

        Returns:
            ApartmentMetadata instance for summary tracking
        """
        filename = Path(filepath).name

        return ApartmentMetadata(
            listing_id=apartment.listing_id,
            filename=filename,
            investment_score=apartment.investment_score,
            recommendation=apartment.recommendation,
            price=apartment.price,
            size_sqm=apartment.size_sqm,
            price_per_sqm=apartment.price_per_sqm,
            gross_yield=apartment.gross_yield,
            net_yield=apartment.net_yield,
            monthly_cash_flow=apartment.cash_flow_monthly,  # FIX: correct attribute name
            city=apartment.city,
            postal_code=apartment.postal_code,
            district=apartment.district,
            title=apartment.title,
            source_url=apartment.source_url,
            validation_failed=validation_failed,
            validation_reason=validation_reason,
            scraped_at=apartment.scraped_at,
        )

    def _generate_filename_with_score(self, apartment: ApartmentListing, validation_failed: bool) -> str:
        """
        Generate filename with score prefix for easy sorting.

        Format: YYYY-MM-DD_score_city_district_price.md
        Example: 2025-12-06_8.5_Wien_3_250000.md
                 2025-12-06_nv_Graz_150000.md (validation failed)

        Args:
            apartment: The apartment listing
            validation_failed: Whether validation failed

        Returns:
            Filename string
        """
        timestamp = apartment.scraped_at.strftime("%Y-%m-%d")

        # Score component
        if validation_failed or apartment.investment_score is None:
            score_str = "nv"  # nicht verfügbar
        else:
            score_str = f"{apartment.investment_score:.1f}"

        # Location component - use "nv" for missing city
        if apartment.city:
            city_clean = re.sub(r'[^\w\s-]', '', apartment.city).strip().replace(' ', '_')
        else:
            city_clean = "nv"

        # District component - use "nv" for missing district
        if apartment.district_number:
            district_str = f"_{apartment.district_number}"
        elif apartment.district:
            district_clean = re.sub(r'[^\w\s-]', '', apartment.district).strip().replace(' ', '_')
            district_str = f"_{district_clean}"
        else:
            district_str = "_nv"

        # Price component - use "nv" for missing/invalid price
        if apartment.price and apartment.price > 0:
            price_k = int(apartment.price / 1000)
            price_str = f"{price_k}k"
        else:
            price_str = "nv"

        filename = f"{timestamp}_{score_str}_{city_clean}{district_str}_{price_str}.md"
        return filename

    def _write_apartment_immediately(
        self,
        apartment: ApartmentListing,
        validation_failed: bool = False,
        validation_reason: Optional[str] = None
    ) -> str:
        """
        Write apartment to disk immediately after extraction/analysis.

        Args:
            apartment: The apartment to write
            validation_failed: Whether validation failed
            validation_reason: Reason for validation failure

        Returns:
            Absolute filepath of written file (empty string if write failed)
        """
        import yaml

        try:
            # Generate filename
            filename = self._generate_filename_with_score(apartment, validation_failed)
            filepath = self.apartments_folder / filename

            # Generate YAML frontmatter
            apartment_dict = apartment.to_dict()

            # Add validation status if failed
            if validation_failed:
                apartment_dict['validation'] = {
                    'passed': False,
                    'reason': validation_reason or "Unknown validation error",
                }

            frontmatter = yaml.dump(
                apartment_dict,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False
            )

            # Generate markdown body
            body_lines = []

            # Add validation warning banner if needed
            if validation_failed:
                body_lines.append("> **⚠️ WARNUNG: Validierung fehlgeschlagen**")
                body_lines.append(f"> {validation_reason}")
                body_lines.append(">")
                body_lines.append("> Alle extrahierten Daten wurden dennoch gespeichert für manuelle Prüfung.")
                body_lines.append("")

            # Generate normal markdown content
            md_content = self.md_generator.generate_markdown_content(apartment)
            body_lines.append(md_content)

            body = "\n".join(body_lines)

            # Write atomically (temp file + rename)
            temp_path = filepath.with_suffix('.tmp')
            full_content = f"---\n{frontmatter}---\n\n{body}"

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            # Atomic rename
            temp_path.rename(filepath)

            # Log success
            status = "[VALIDATION FAILED]" if validation_failed else "[OK]"
            score_display = "n/a" if validation_failed or apartment.investment_score is None else f"{apartment.investment_score:.1f}"
            logger.info(
                f"{status} Written: {filename} (Score: {score_display})"
            )

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to write apartment {apartment.listing_id}: {e}")
            return ""

    async def process_apartment(
        self, crawler: AsyncWebCrawler, url: str
    ) -> Optional[ApartmentMetadata]:
        """
        Fetch and process a single apartment listing.

        Args:
            crawler: The web crawler instance
            url: Apartment listing URL

        Returns:
            Processed ApartmentListing or None if failed/filtered
        """
        listing_id = self.extract_listing_id(url)

        # Check for duplicates
        if listing_id in self.seen_listings:
            logger.debug(f"Skipping duplicate: {listing_id}")
            return None

        self.seen_listings.add(listing_id)

        try:
            result = await crawler.arun(
                url=url,
                wait_for="css:main",
                delay_before_return_html=2.0,
            )

            if not result.success:
                logger.warning(f"Failed to fetch: {url}")
                return None

            # Extract apartment data
            apartment = await self.extract_apartment_data(result.html, url)
            if not apartment:
                return None

            # Apply price filter - discard apartments above max_price
            max_price = self.filters.get("max_price")
            if max_price and apartment.price and apartment.price > max_price:
                logger.info(
                    f"Filtering out apartment {listing_id}: price €{apartment.price:,.0f} "
                    f"exceeds max_price €{max_price:,.0f}"
                )
                return None

            # Validate critical fields (but still write even if validation fails)
            is_valid, validation_reason = self._validate_critical_fields(apartment)

            # Perform investment analysis (even if validation failed - gives partial metrics)
            apartment = self.analyzer.analyze_apartment(apartment)

            # Generate LLM summary if enabled (only for valid apartments)
            if is_valid and self.generate_llm_summary and self.summarizer:
                try:
                    summary_timeout = self.config.get("llm_settings", {}).get("summary_timeout", 120)
                    summary = await asyncio.wait_for(
                        self.summarizer.generate_summary(apartment),
                        timeout=summary_timeout,  # Use configured timeout (was 90s, now 120s)
                    )
                    if summary:
                        apartment.llm_summary = summary
                        apartment.llm_summary_generated_at = datetime.now()
                        logger.info(f"LLM summary generated ({len(summary)} chars)")
                except asyncio.TimeoutError:
                    logger.warning(f"Summary generation timed out for {listing_id}")
                except Exception as e:
                    logger.warning(f"Summary generation failed for {listing_id}: {e}")

            # NEW: Write immediately to disk (ALL apartments, including validation failures)
            filepath = self._write_apartment_immediately(
                apartment,
                validation_failed=not is_valid,
                validation_reason=validation_reason
            )

            if not filepath:
                # Disk write failed - log error but continue
                logger.error(f"Failed to write apartment {listing_id} to disk")
                return None

            # NEW: Extract and store lightweight metadata
            metadata = self._extract_metadata(
                apartment,
                filepath,
                validation_failed=not is_valid,
                validation_reason=validation_reason
            )
            logger.debug(f"Created metadata for {apartment.listing_id}: {metadata.filename}")
            self.apartment_metadata.append(metadata)
            logger.debug(f"Metadata list now has {len(self.apartment_metadata)} items")

            # NEW: Track top N for PDF (only valid apartments)
            if is_valid:
                self.top_n_tracker.add(apartment)

            return metadata

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None

    async def scrape_page(
        self, crawler: AsyncWebCrawler, page: int
    ) -> List[ApartmentMetadata]:
        """
        Scrape a single page of listings.

        Args:
            crawler: The web crawler instance
            page: Page number to scrape

        Returns:
            List of apartment metadata from this page
        """
        url = self.build_willhaben_url(page)
        logger.info(f"Scraping page {page}: {url}")

        result = await crawler.arun(
            url=url,
            wait_for="css:section",
            delay_before_return_html=3.0,
            js_code="window.scrollTo(0, document.body.scrollHeight);",
        )

        if not result.success:
            logger.error(f"Failed to scrape page {page}: {result.error_message}")
            return []

        # Extract listing URLs
        listings = self.extract_listing_urls(result.html)
        logger.info(f"Found {len(listings)} listings on page {page}")

        if not listings:
            return []

        # Process each listing
        page_apartments = []
        total_so_far = len(self.apartment_metadata)
        for i, listing in enumerate(listings, 1):
            listing_url = listing["url"]
            logger.info(
                f"  [{i}/{len(listings)}] Processing apartment (Total so far: {total_so_far}): {listing_url}"
            )

            metadata = await self.process_apartment(crawler, listing_url)
            if metadata:
                page_apartments.append(metadata)
                total_so_far = len(self.apartment_metadata)

            # Rate limiting
            await asyncio.sleep(self.delay_apartment)

        return page_apartments

    async def run(self) -> List[ApartmentMetadata]:
        """
        Run the full scraping process with immediate disk writing.

        Returns:
            List of apartment metadata for all processed apartments
        """
        max_pages = self.config.get("max_pages")
        consecutive_empty_pages = 0
        max_consecutive_empty = 2
        page = 1

        logger.info(f"Starting scrape (max_pages: {max_pages or 'unlimited'})")

        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            while True:
                # Check page limit
                if max_pages and page > max_pages:
                    logger.info(f"Reached max page limit ({max_pages})")
                    break

                # Scrape page
                page_apartments = await self.scrape_page(crawler, page)

                if page_apartments:
                    consecutive_empty_pages = 0
                    logger.info(
                        f"Page {page}: {len(page_apartments)} apartments "
                        f"(Total: {len(self.apartment_metadata)})"
                    )
                else:
                    consecutive_empty_pages += 1
                    logger.info(
                        f"Page {page}: Empty ({consecutive_empty_pages}/{max_consecutive_empty})"
                    )

                    if consecutive_empty_pages >= max_consecutive_empty:
                        logger.info("Stopping: consecutive empty pages limit reached")
                        break

                # Rate limiting between pages
                await asyncio.sleep(self.delay_page)
                page += 1

        logger.info(f"Scraping complete: {len(self.apartment_metadata)} apartments")

        # NEW: Generate complete summary with ALL apartments
        if self.generate_summary:
            if len(self.apartment_metadata) == 0:
                logger.warning("No apartments collected - summary will be empty!")
            else:
                logger.info(f"Generating summary for {len(self.apartment_metadata)} apartments")
            self._generate_complete_summary()

            # Generate PDF with top N apartments
            if self.config.get("output", {}).get("generate_pdf", True):
                self._generate_pdf_report()

        return self.apartment_metadata

    def _generate_complete_summary(self) -> None:
        """
        Generate summary.md with ALL apartments (sorted by score).

        Includes:
        - Statistics section (total count, valid/invalid, averages, city breakdown)
        - Complete table with ALL apartments
        - Validation failures marked with warnings
        """
        from collections import Counter

        logger.info(f"Starting summary generation with {len(self.apartment_metadata)} apartments")

        # Summary goes inside the run folder
        summary_path = self.run_folder / "summary.md"

        # Sort metadata by score (validation failures at bottom)
        sorted_metadata = sorted(
            self.apartment_metadata,
            key=lambda m: (not m.validation_failed, m.investment_score or -1),
            reverse=True
        )

        logger.debug(f"Sorted {len(sorted_metadata)} apartments for summary")

        # Calculate statistics
        total = len(sorted_metadata)
        valid_count = sum(1 for m in sorted_metadata if not m.validation_failed)
        failed_count = total - valid_count

        # Average scores (only valid apartments)
        valid_metadata = [m for m in sorted_metadata if not m.validation_failed and m.investment_score is not None]
        avg_score = sum(m.investment_score for m in valid_metadata) / valid_count if valid_count > 0 else 0

        # Average yield (only valid apartments)
        valid_yields = [m.gross_yield for m in valid_metadata if m.gross_yield is not None]
        avg_yield = sum(valid_yields) / len(valid_yields) if valid_yields else 0

        # City breakdown
        city_counts = Counter(m.city for m in sorted_metadata if m.city)

        # Generate report
        timestamp = self.run_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Display postal codes if available, otherwise area_ids
        if "postal_codes" in self.config:
            location_str = ", ".join(str(plz) for plz in self.config["postal_codes"])
        else:
            location_str = ", ".join(str(aid) for aid in self.area_ids)

        content = [
            "# Investment Summary - Alle Wohnungen",
            "",
            f"**Generiert:** {timestamp}",
            f"**Run ID:** {self.run_id}",
            f"**Portal:** {self.portal}",
            f"**Postleitzahlen:** {location_str}",
            "",
            "## Statistik",
            "",
            f"- **Gesamt:** {total} Wohnungen",
            f"- **Valide:** {valid_count}",
            f"- **Validierung fehlgeschlagen:** {failed_count}",
            f"- **Durchschnittliche Bewertung:** {avg_score:.1f}/10",
            f"- **Durchschnittliche Rendite:** {avg_yield:.1f}%",
            "",
        ]

        # City breakdown
        if city_counts:
            content.append("**Verteilung nach Städten:**")
            for city, count in city_counts.most_common():
                content.append(f"- {city}: {count}")
            content.append("")

        # Validation failures section (for debugging)
        if failed_count > 0:
            content.extend([
                "## ⚠️ Validierung fehlgeschlagen",
                "",
                f"**{failed_count} Wohnung(en) mit fehlenden kritischen Feldern:**",
                "",
                "| Nr. | Grund | Preis | Größe | BK/Monat | Lage | Details |",
                "|-----|-------|-------|-------|----------|------|---------|",
            ])

            failed_metadata = [m for m in sorted_metadata if m.validation_failed]
            for idx, meta in enumerate(failed_metadata, 1):
                reason = meta.validation_reason or "Unbekannter Validierungsfehler"
                price_str = f"€{meta.price:,.0f}" if meta.price else "❌ fehlt"
                size_str = f"{meta.size_sqm:.0f}m²" if meta.size_sqm and meta.size_sqm >= 10 else "❌ fehlt"

                # Try to get betriebskosten from listing if available (not in metadata)
                bk_str = "n/a"  # Metadata doesn't have this field

                location_parts = []
                if meta.postal_code:
                    location_parts.append(meta.postal_code)
                if meta.city:
                    location_parts.append(meta.city)
                location = " ".join(location_parts) if location_parts else "n/a"

                details_link = f"[Details](apartments/{meta.filename})"

                content.append(
                    f"| {idx} | {reason} | {price_str} | {size_str} | {bk_str} | {location} | {details_link} |"
                )

            content.append("")

        content.extend([
            "## Alle Wohnungen (sortiert nach Bewertung)",
            "",
            f"| Rang | Status | Bewertung | Empfehlung | Preis | Größe | Rendite | Lage | Details |",
            "|------|--------|-----------|------------|-------|-------|---------|------|---------|",
        ])

        for rank, meta in enumerate(sorted_metadata, 1):
            # Status indicator
            if meta.validation_failed:
                status = "⚠️"
                score_str = "n/v"
            else:
                status = "✅"
                score_str = f"{meta.investment_score:.1f}" if meta.investment_score is not None else "n/a"

            recommendation = meta.recommendation or "n/a"
            if recommendation in RECOMMENDATIONS:
                recommendation = RECOMMENDATIONS[recommendation]

            price_str = f"€{meta.price:,.0f}" if meta.price else "n/a"
            size_str = f"{meta.size_sqm:.0f}m²" if meta.size_sqm else "n/a"
            yield_str = f"{meta.gross_yield:.1f}%" if meta.gross_yield else "n/a"

            # Location string
            location_parts = []
            if meta.postal_code:
                location_parts.append(meta.postal_code)
            if meta.city:
                location_parts.append(meta.city)
            location = " ".join(location_parts) if location_parts else "n/a"

            # Details link to apartments/ subfolder
            details_link = f"[Details](apartments/{meta.filename})"

            content.append(
                f"| {rank} | {status} | {score_str} | {recommendation} | {price_str} | "
                f"{size_str} | {yield_str} | {location} | {details_link} |"
            )

        content.extend(["", "---", "", "*Generiert mit noessi-crawl*"])

        # Write summary
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))

        logger.info(f"Complete summary saved: {summary_path} ({len(sorted_metadata)} apartments, {failed_count} failed)")

    def _generate_pdf_report(self) -> None:
        """Generate PDF report with top N apartments (from TopNTracker)."""
        # Get sorted top N apartments (full objects from heap)
        top_apartments = self.top_n_tracker.get_sorted_apartments()

        if not top_apartments:
            logger.warning("No valid apartments for PDF report")
            return

        # PDF goes inside the run folder
        pdf_filename = self.config.get("output", {}).get("pdf_filename", "investment_summary.pdf")
        pdf_path = self.run_folder / pdf_filename

        try:
            # Initialize PDF generator
            pdf_generator = PDFGenerator(
                output_dir=str(self.run_folder),
                run_timestamp=self.run_timestamp,
                config=self.config
            )

            # Generate PDF
            output_path = pdf_generator.generate_pdf_report(
                apartments=top_apartments,
                filename=pdf_filename
            )

            logger.info(f"PDF report saved: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)

    def _build_location_string(self, apt: ApartmentListing) -> str:
        """Build simple location string: postal_code + city."""
        location_parts = []

        # Simple format: postal code + city
        if apt.postal_code:
            location_parts.append(apt.postal_code)
        if apt.city:
            location_parts.append(apt.city)

        return " ".join(location_parts) if location_parts else PHRASES["n/a"]

    def _save_diagnostic_data(
        self,
        listing_id: str,
        url: str,
        html: str,
        json_ld_data: Optional[Dict[str, Any]],
        regex_data: Dict[str, Any],
        llm_data: Optional[Dict[str, Any]],
        apartment: ApartmentListing
    ) -> None:
        """Save diagnostic extraction data for debugging."""
        diagnostic_dir = Path("diagnostics")
        diagnostic_dir.mkdir(exist_ok=True)

        diagnostic_file = diagnostic_dir / f"{listing_id}_extraction.json"

        diagnostic_data = {
            "listing_id": listing_id,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "extraction_results": {
                "json_ld": json_ld_data,
                "regex": regex_data,
                "llm": llm_data,
            },
            "final_apartment": apartment.to_dict(),
            "html_excerpt": html[:5000] if html else None,  # First 5000 chars for inspection
            "html_length": len(html) if html else 0,
        }

        try:
            with open(diagnostic_file, "w", encoding="utf-8") as f:
                json.dump(diagnostic_data, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(f"Saved diagnostic data to {diagnostic_file}")
        except Exception as e:
            logger.warning(f"Failed to save diagnostic data: {e}")


async def load_config() -> Dict[str, Any]:
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Validate required fields
    if "portal" not in config:
        raise ValueError("Missing required field 'portal' in config.json")

    if config["portal"] == "willhaben":
        # Support both postal_codes (new) and area_ids (legacy)
        if "postal_codes" not in config and "area_ids" not in config:
            raise ValueError(
                "Missing required field 'postal_codes' or 'area_ids' for willhaben portal"
            )

    # Ensure output folder exists
    output_folder = Path(__file__).parent / config.get("output_folder", "output")
    output_folder.mkdir(exist_ok=True)

    return config


async def main():
    """Main entry point for the apartment scraper."""
    try:
        config = await load_config()

        if config["portal"] != "willhaben":
            logger.error(f"Unsupported portal: {config['portal']}")
            return

        scraper = EnhancedApartmentScraper(config)
        apartments = await scraper.run()

        logger.info(
            f"Scraping complete! Found {len(apartments)} investment opportunities."
        )

    except FileNotFoundError:
        logger.error("config.json not found")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
