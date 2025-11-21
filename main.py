import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from crawl4ai import *


async def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Validate required fields
    if "portal" not in config:
        raise ValueError("Missing required field 'portal' in config.json")

    if config["portal"] == "willhaben":
        if "area_ids" not in config:
            raise ValueError("Missing required field 'area_ids' for willhaben portal")
        if "price_max" not in config:
            raise ValueError("Missing required field 'price_max' for willhaben portal")
        if not isinstance(config["area_ids"], list):
            raise ValueError("Field 'area_ids' must be a list of integers")
        if not isinstance(config["price_max"], (int, float)):
            raise ValueError("Field 'price_max' must be a number")

    # Ensure output folder exists
    output_folder = Path(__file__).parent / config.get("output_folder", "output")
    output_folder.mkdir(exist_ok=True)

    return config


def build_willhaben_url(area_ids: list, price_max: int) -> str:
    """
    Build willhaben.at search URL from configuration parameters

    Args:
        area_ids: List of postal code area IDs (e.g., [201, 202, 203])
        price_max: Maximum price threshold

    Returns:
        Complete willhaben.at search URL with query parameters
    """
    base_url = "https://www.willhaben.at/iad/immobilien/eigentumswohnung/eigentumswohnung-angebote"

    # Build query parameters
    params = []

    # Add area IDs
    for area_id in area_ids:
        params.append(f"areaId={area_id}")

    # Add price threshold
    params.append(f"PRICE_TO={int(price_max)}")

    # Add navigation flag (based on existing URL pattern)
    params.append("isNavigation=true")

    # Combine into final URL
    url = f"{base_url}?{'&'.join(params)}"

    return url


async def scrape_apartments(url: str) -> list:
    """
    Scrape apartment listings from willhaben.at

    Args:
        url: The filtered willhaben.at URL with search parameters

    Returns:
        List of apartment dictionaries with extracted data
    """
    print("🏠 Starting apartment scraper...")
    print(f"📍 Target URL: {url}")

    # Crawl the webpage
    async with AsyncWebCrawler(headless=True, verbose=True) as crawler:
        print("🌐 Crawling webpage...")

        result = await crawler.arun(
            url=url,
            wait_for="css:section",
            delay_before_return_html=3.0,
            js_code="window.scrollTo(0, document.body.scrollHeight);",
        )

        if not result.success:
            print(f"❌ Crawl failed: {result.error_message}")
            return []

        print("✅ Webpage crawled successfully")
        print(f"📄 HTML length: {len(result.html)} chars")

        # Extract JSON-LD structured data
        print("🔍 Extracting apartment data from structured data...")
        apartments = extract_apartments_from_html(result.html)

        if apartments:
            print(f"📊 Found {len(apartments)} apartments from JSON-LD")

            # Now fetch details for each apartment
            print("📝 Fetching detailed information for each apartment...")
            detailed_apartments = []

            for i, apt in enumerate(
                apartments[:30], 1
            ):  # Limit to first 30 to avoid rate limiting
                url = apt.get("url", "")
                if url:
                    print(f"  [{i}/{min(len(apartments), 30)}] Fetching: {url}")
                    details = await fetch_apartment_details(crawler, url)
                    if details:
                        detailed_apartments.append(details)
                    # Small delay to be polite
                    await asyncio.sleep(0.5)

            return detailed_apartments
        else:
            print("⚠️ No apartments found in JSON-LD data")
            return []


def extract_apartments_from_html(html: str) -> list:
    """Extract apartment URLs from JSON-LD structured data"""
    try:
        # Find the JSON-LD script tag
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
        print(f"⚠️ Error extracting JSON-LD: {e}")

    return []


async def fetch_apartment_details(crawler, url: str) -> dict:
    """Fetch details for a single apartment"""
    try:
        result = await crawler.arun(
            url=url, wait_for="css:main", delay_before_return_html=2.0
        )

        if not result.success:
            return None

        html = result.html

        # Filter out ads - check for star icon SVG path (indicates real listing)
        star_icon_path = "m12 4 2.09 4.25a1.52 1.52 0 0 0 1.14.82l4.64.64-3.42 3.32"
        if star_icon_path not in html:
            # This is an ad or promoted listing without the star icon
            return None

        # Extract details from the page
        details = {
            "link": url,
            "title": "N/A",
            "price": "N/A",
            "square_meters": "N/A",
            "price_per_sqm": "N/A",
            "energy_class": "N/A",
            "location": "N/A",
        }

        markdown = result.markdown

        # Extract title from markdown (cleaner) - skip cookie/generic text
        title_match = re.search(r"^## (.+)$", markdown, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Skip generic titles
            if "cookie" not in title.lower() and title != "N/A":
                # Replace pipes with dash to avoid breaking markdown table formatting
                details["title"] = title.replace("|", "—")

        # Extract price - look for JSON-LD data (more reliable)
        price_match = re.search(r'"price"[:\s]*"?(\d+(?:\.\d+)*)"?', html)
        if price_match:
            price_val = float(price_match.group(1))
            details["price"] = f"€ {int(price_val):,}".replace(",", ".")

        # Extract square meters
        sqm_match = re.search(r"(\d+(?:,\d+)?)\s*m²", html)
        if sqm_match:
            sqm_val = sqm_match.group(1).replace(",", ".")
            details["square_meters"] = f"{sqm_val} m²"

            # Calculate price per sqm if we have both
            if price_match:
                try:
                    price_num = float(price_match.group(1))
                    sqm_num = float(sqm_val)
                    price_per_sqm = price_num / sqm_num
                    details["price_per_sqm"] = f"€ {price_per_sqm:,.0f}/m²".replace(
                        ",", "."
                    )
                except:
                    pass

        # Extract energy class
        energy_match = re.search(
            r"Energie[kK]lasse[:\s]*([A-G][+]?)", html, re.IGNORECASE
        )
        if energy_match:
            details["energy_class"] = energy_match.group(1)

        # Extract location from URL
        if "wien" in url.lower():
            # Extract district from URL pattern like "wien-1030-landstrasse"
            # Vienna postal codes: 1030 = 3rd district, 1050 = 5th, etc.
            # Pattern: last 2 digits / 10 = district (30/10=3, 50/10=5, 20/10=2)
            district_match = re.search(r"/wien-\d{2}(\d{2})-", url)
            if district_match:
                last_two = int(district_match.group(1))
                district_num = last_two // 10  # Integer division: 30//10=3, 50//10=5
                details["location"] = f"Wien, {district_num}. Bezirk"
            else:
                details["location"] = "Wien"
        elif "klagenfurt" in url.lower():
            details["location"] = "Klagenfurt"
        elif "villach" in url.lower():
            details["location"] = "Villach"

        return details

    except Exception as e:
        print(f"    ⚠️ Error fetching {url}: {e}")
        return None


def generate_markdown(apartments: list, config: dict, url: str) -> str:
    """
    Generate markdown formatted output for apartment listings

    Args:
        apartments: List of apartment dictionaries
        config: Configuration dictionary with portal settings
        url: Generated search URL

    Returns:
        Markdown formatted string
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Format area IDs for display
    area_ids_str = ", ".join(str(aid) for aid in config.get("area_ids", []))

    md_content = f"""# Willhaben.at Apartment Investment Opportunities

**Generated:** {timestamp}
**Portal:** {config.get("portal", "N/A")}
**Area IDs (PLZ):** {area_ids_str}
**Max Price:** € {config.get("price_max", "N/A"):,}
**Total Listings Found:** {len(apartments)}

<details>
<summary>Search URL</summary>

{url}
</details>

---

## Apartment Listings

| Title | Price | m² | €/m² | Energy Class | Location | Link |
|-------|-------|-----|------|--------------|----------|------|
"""

    for apt in apartments:
        title = (
            apt.get("title", "N/A")[:50] + "..."
            if len(apt.get("title", "")) > 50
            else apt.get("title", "N/A")
        )
        price = apt.get("price", "N/A")
        sqm = apt.get("square_meters", "N/A")
        price_per_sqm = apt.get("price_per_sqm", "N/A")
        energy_class = apt.get("energy_class", "N/A")
        location = apt.get("location", "N/A")
        link = apt.get("link", "#")

        md_content += f"| {title} | {price} | {sqm} | {price_per_sqm} | {energy_class} | {location} | [View]({link}) |\n"

    if not apartments:
        md_content += "| No apartments found | - | - | - | - | - | - |\n"

    md_content += "\n---\n\n*Data extracted using crawl4ai*\n"

    return md_content


async def main():
    """Main entry point for the apartment scraper"""
    try:
        # Load configuration
        config = await load_config()
        output_folder = config.get("output_folder", "output")

        # Build URL based on portal configuration
        if config["portal"] == "willhaben":
            url = build_willhaben_url(
                area_ids=config["area_ids"], price_max=config["price_max"]
            )
        else:
            print(f"❌ Error: Unsupported portal '{config['portal']}'")
            return

        # Scrape apartments
        apartments = await scrape_apartments(url)

        # Generate markdown output
        markdown_content = generate_markdown(apartments, config, url)

        # Write to file in output folder
        output_file = Path(__file__).parent / output_folder / "apartments.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"\n✅ Success! Apartment listings saved to: {output_file}")
        print(f"📝 Total apartments extracted: {len(apartments)}")

    except FileNotFoundError:
        print("❌ Error: config.json not found")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
