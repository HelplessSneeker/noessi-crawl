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
from models.apartment import ApartmentListing
from models.constants import AREA_ID_TO_LOCATION, PLZ_TO_AREA_ID
from utils.address_parser import AustrianAddressParser
from utils.extractors import AustrianRealEstateExtractor
from utils.markdown_generator import MarkdownGenerator
from utils.translations import HEADERS, LABELS, PHRASES, RECOMMENDATIONS, TABLE_HEADERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
        extraction_config = config.get("extraction", {})
        self.use_llm = extraction_config.get("use_llm", False)
        self.fallback_to_regex = extraction_config.get("fallback_to_regex", True)

        if self.use_llm:
            llm_model = extraction_config.get("llm_model", "qwen3:8b")
            self.llm_extractor = OllamaExtractor(model=llm_model)
        else:
            self.llm_extractor = None

        # Investment analyzer
        analysis_config = config.get("analysis", {})
        self.analyzer = InvestmentAnalyzer(analysis_config)

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
        self.summary_top_n = output_config.get("summary_top_n", 20)

        # Rate limiting
        rate_config = config.get("rate_limiting", {})
        self.delay_apartment = rate_config.get("delay_apartment", 0.5)
        self.delay_page = rate_config.get("delay_page", 1.0)

        # Tracking
        self.seen_listings: Set[str] = set()
        self.processed_apartments: List[ApartmentListing] = []
        self.apartment_files: Dict[str, str] = {}  # listing_id -> filepath

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

        # Add price threshold
        price_max = self.config.get("price_max")
        if price_max:
            params.append(f"PRICE_TO={int(price_max)}")

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

        # Strategy 2: Extract using regex patterns
        regex_data = self.extractor.extract_from_html(html)
        self._apply_regex_data(apartment, regex_data)

        # Extract address
        address_text = self._extract_address_from_html(html, url)
        if address_text:
            parsed_address = self.address_parser.parse_address(address_text)
            self._apply_address_data(apartment, parsed_address)

        # Strategy 3: LLM extraction (if enabled and missing critical fields)
        if self.use_llm and self.llm_extractor:
            missing_critical = not apartment.price or not apartment.size_sqm
            if missing_critical or self._has_missing_fields(apartment):
                logger.info(
                    f"Starting LLM extraction for listing {listing_id} "
                    f"(missing critical: {missing_critical})"
                )
                existing_data = apartment.to_dict()
                try:
                    # Add hard timeout wrapper to prevent indefinite hangs
                    llm_data = await asyncio.wait_for(
                        self.llm_extractor.extract_structured_data(html, existing_data),
                        timeout=180.0,  # 3 minutes max for LLM extraction
                    )
                    logger.info(f"LLM extraction completed for listing {listing_id}")
                    self._apply_llm_data(apartment, llm_data)
                except asyncio.TimeoutError:
                    logger.error(
                        f"LLM extraction timed out after 180s for listing {listing_id}, "
                        f"continuing without LLM data"
                    )
                except Exception as e:
                    logger.error(f"LLM extraction failed for listing {listing_id}: {e}")
            else:
                logger.debug(
                    f"Skipping LLM extraction for {listing_id} - all fields present"
                )

        # Extract title from markdown/HTML if not set
        if not apartment.title:
            apartment.title = self._extract_title(html)

        # Enrich location data from area_ids if missing
        self._enrich_location_from_area_ids(apartment)

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

    def _apply_regex_data(
        self, apartment: ApartmentListing, data: Dict[str, Any]
    ) -> None:
        """Apply regex-extracted data to apartment."""
        # Only apply if not already set
        if not apartment.price and "price" in data:
            apartment.price = data["price"]
        if not apartment.size_sqm and "size_sqm" in data:
            apartment.size_sqm = data["size_sqm"]
        if not apartment.rooms and "rooms" in data:
            apartment.rooms = data["rooms"]

        # Apply other fields
        field_mappings = [
            "betriebskosten_monthly",
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

    def _apply_llm_data(
        self, apartment: ApartmentListing, data: Dict[str, Any]
    ) -> None:
        """Apply LLM-extracted data to apartment (only missing fields)."""
        # Only fill in missing fields
        if not apartment.title and data.get("title"):
            apartment.title = data["title"]
        if not apartment.price and data.get("price"):
            apartment.price = data["price"]
        if not apartment.size_sqm and data.get("size_sqm"):
            apartment.size_sqm = data["size_sqm"]
        if not apartment.rooms and data.get("rooms"):
            apartment.rooms = data["rooms"]
        if not apartment.bedrooms and data.get("bedrooms"):
            apartment.bedrooms = data["bedrooms"]
        if not apartment.bathrooms and data.get("bathrooms"):
            apartment.bathrooms = data["bathrooms"]
        if apartment.floor is None and data.get("floor") is not None:
            apartment.floor = data["floor"]
        if not apartment.year_built and data.get("year_built"):
            apartment.year_built = data["year_built"]
        if not apartment.condition and data.get("condition"):
            apartment.condition = data["condition"]
        if not apartment.building_type and data.get("building_type"):
            apartment.building_type = data["building_type"]
        if not apartment.energy_rating and data.get("energy_rating"):
            apartment.energy_rating = data["energy_rating"]
        if not apartment.heating_type and data.get("heating_type"):
            apartment.heating_type = data["heating_type"]

        # Address from LLM
        if data.get("address") and not apartment.full_address:
            parsed = self.address_parser.parse_address(data["address"])
            self._apply_address_data(apartment, parsed)

    def _has_missing_fields(self, apartment: ApartmentListing) -> bool:
        """Check if apartment has important missing fields."""
        important_fields = ["rooms", "year_built", "condition", "energy_rating"]
        return any(getattr(apartment, f) is None for f in important_fields)

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

    async def process_apartment(
        self, crawler: AsyncWebCrawler, url: str
    ) -> Optional[ApartmentListing]:
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

            # Perform investment analysis
            apartment = self.analyzer.analyze_apartment(apartment)

            # Store all apartments - sorting and file generation happens at the end
            self.processed_apartments.append(apartment)
            logger.info(
                f"Processed: {apartment.title or listing_id} "
                f"(Score: {apartment.investment_score:.1f})"
            )
            return apartment

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None

    async def scrape_page(
        self, crawler: AsyncWebCrawler, page: int
    ) -> List[ApartmentListing]:
        """
        Scrape a single page of listings.

        Args:
            crawler: The web crawler instance
            page: Page number to scrape

        Returns:
            List of processed apartments from this page
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
        total_so_far = len(self.processed_apartments)
        for i, listing in enumerate(listings, 1):
            listing_url = listing["url"]
            logger.info(
                f"  [{i}/{len(listings)}] Processing apartment (Total so far: {total_so_far}): {listing_url}"
            )

            apartment = await self.process_apartment(crawler, listing_url)
            if apartment:
                page_apartments.append(apartment)
                total_so_far = len(self.processed_apartments)

            # Rate limiting
            await asyncio.sleep(self.delay_apartment)

        return page_apartments

    async def run(self) -> List[ApartmentListing]:
        """
        Run the full scraping process.

        Returns:
            List of all processed apartments
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
                        f"(Total: {len(self.processed_apartments)})"
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

        logger.info(f"Scraping complete: {len(self.processed_apartments)} apartments")

        # Sort and save apartments - top N to active, rest to rejected
        self._save_apartments()

        # Generate summary report
        if self.generate_summary:
            self._generate_summary_report()

        return self.processed_apartments

    def _save_apartments(self) -> None:
        """Save apartments to files - top N to active, rest to rejected."""
        # Sort by investment score (highest first)
        sorted_apartments = sorted(
            self.processed_apartments,
            key=lambda a: a.investment_score or 0,
            reverse=True,
        )

        # Top N go to active folder (these appear in summary)
        active_apartments = sorted_apartments[: self.summary_top_n]
        # Rest go to rejected folder
        rejected_apartments = sorted_apartments[self.summary_top_n :]

        logger.info(
            f"Saving {len(active_apartments)} to active, "
            f"{len(rejected_apartments)} to rejected"
        )

        # Save active apartments
        for apt in active_apartments:
            filepath = self.md_generator.generate_apartment_file(apt, rejected=False)
            self.apartment_files[apt.listing_id] = filepath
            logger.info(
                f"Active: {apt.title or apt.listing_id} (Score: {apt.investment_score:.1f})"
            )

        # Save rejected apartments
        for apt in rejected_apartments:
            reason = f"Rang #{sorted_apartments.index(apt) + 1} (unterhalb Top {self.summary_top_n})"
            filepath = self.md_generator.generate_apartment_file(
                apt, rejected=True, rejection_reason=reason
            )
            self.apartment_files[apt.listing_id] = filepath
            logger.debug(f"Rejected: {apt.title or apt.listing_id} - {reason}")

    def _generate_summary_report(self) -> None:
        """Generate summary report of all processed apartments."""
        # Summary goes inside the run folder
        summary_path = self.run_folder / "summary_report.md"

        # Sort by investment score
        sorted_apartments = sorted(
            self.processed_apartments,
            key=lambda a: a.investment_score or 0,
            reverse=True,
        )

        # Generate report
        timestamp = self.run_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Display postal codes if available, otherwise area_ids
        if "postal_codes" in self.config:
            location_str = ", ".join(str(plz) for plz in self.config["postal_codes"])
        else:
            location_str = ", ".join(str(aid) for aid in self.area_ids)

        # Calculate active/rejected counts
        total = len(self.processed_apartments)
        active_count = min(self.summary_top_n, total)
        rejected_count = max(0, total - self.summary_top_n)

        content = [
            f"# {HEADERS['investment_summary_report']}",
            "",
            f"**{LABELS['generated']}:** {timestamp}",
            f"**{LABELS['run_id']}:** {self.run_id}",
            f"**{LABELS['portal']}:** {self.portal}",
            f"**{LABELS['postal_codes']}:** {location_str}",
            f"**{LABELS['max_price']}:** EUR {self.config.get('price_max', PHRASES['n/a']):,}",
            f"**{LABELS['total_scraped']}:** {total}",
            f"**{LABELS['active']} ({LABELS['top']} {self.summary_top_n}):** {active_count}",
            f"**{LABELS['rejected']}:** {rejected_count}",
            "",
            "---",
            "",
            f"## {LABELS['top']} {active_count} {HEADERS['top_opportunities']}",
            "",
            f"| {TABLE_HEADERS['rank']} | {TABLE_HEADERS['score']} | {TABLE_HEADERS['recommendation']} | {TABLE_HEADERS['price']} | {TABLE_HEADERS['size']} | {TABLE_HEADERS['yield']} | {TABLE_HEADERS['location']} | {TABLE_HEADERS['details']} | {TABLE_HEADERS['source']} |",
            "|------|-------|----------------|-------|------|-------|----------|---------|--------|",
        ]

        for i, apt in enumerate(sorted_apartments[: self.summary_top_n], 1):
            price = f"EUR {apt.price:,.0f}" if apt.price else PHRASES["n/a"]
            size = f"{apt.size_sqm:.0f}m²" if apt.size_sqm else PHRASES["n/a"]
            yield_str = f"{apt.gross_yield:.1f}%" if apt.gross_yield else PHRASES["n/a"]

            # Translate recommendation to German
            recommendation = apt.recommendation or PHRASES["n/a"]
            if recommendation in RECOMMENDATIONS:
                recommendation = RECOMMENDATIONS[recommendation]

            # Build location string with fallback to area_id mapping
            location = self._build_location_string(apt)

            # Get local file link (relative to summary report in same folder)
            local_file = self.apartment_files.get(apt.listing_id, "")
            if local_file:
                filename = Path(local_file).name
                details_link = f"[{LABELS['details']}](active/{filename})"
            else:
                details_link = "-"

            content.append(
                f"| {i} | {apt.investment_score:.1f} | {recommendation} | "
                f"{price} | {size} | {yield_str} | {location} | "
                f"{details_link} | [{LABELS['source']}]({apt.source_url}) |"
            )

        content.append("")
        content.append("---")
        content.append("")
        content.append(f"*{PHRASES['generated_by']}*")

        # Write report
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        logger.info(f"Summary report saved: {summary_path}")

    def _build_location_string(self, apt: ApartmentListing) -> str:
        """Build simple location string: postal_code + city."""
        location_parts = []

        # Simple format: postal code + city
        if apt.postal_code:
            location_parts.append(apt.postal_code)
        if apt.city:
            location_parts.append(apt.city)

        return " ".join(location_parts) if location_parts else PHRASES["n/a"]


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
        if "price_max" not in config:
            raise ValueError("Missing required field 'price_max' for willhaben portal")

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
