"""Fetch HTML fixture for betriebskosten extraction testing.

This script fetches a real willhaben.at apartment that currently shows
betriebskosten: 1.0 (incorrect) and saves the HTML for testing.

Expected betriebskosten from manual inspection of the willhaben.at page:
Will need to be added after fetching and inspecting the HTML.
"""

import asyncio
from pathlib import Path

from crawl4ai import AsyncWebCrawler


async def fetch_fixture():
    """Fetch apartment HTML and save as test fixture"""

    # Apartment that currently shows betriebskosten: 1.0
    url = "https://www.willhaben.at/iad/immobilien/d/eigentumswohnung/kaernten/klagenfurt/lichtdurchflutete-wohnung-mit-kleinem-balkon-2061847835/"

    print(f"Fetching: {url}")

    async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
        result = await crawler.arun(
            url=url,
            wait_for="css:main",
            delay_before_return_html=2.0
        )

        if not result.success:
            print(f"❌ Failed to fetch: {result.error_message}")
            return

        print("✅ Fetch successful")

        # Create fixtures directory
        fixtures_dir = Path(__file__).parent / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)

        # Save HTML
        fixture_path = fixtures_dir / "betriebskosten_klagenfurt_180k.html"
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write(result.html)

        print(f"Saved HTML fixture to: {fixture_path}")
        print(f"Size: {len(result.html):,} chars")

        # Try to find betriebskosten in HTML for manual verification
        print("\n=== SEARCHING FOR BETRIEBSKOSTEN ===")
        import re

        # Search for betriebskosten patterns
        patterns = [
            (r"Betriebskosten[:\s]*€?\s*([\d.,]+)", "Betriebskosten direct"),
            (r"BK[:\s]*€?\s*([\d.,]+)", "BK direct"),
            (r">Betriebskosten</.*?>.*?€\s*([\d.,]+)", "Betriebskosten in table"),
            (r"€\s*([\d.,]+).*?Betriebskosten", "Euro before label"),
        ]

        for pattern, desc in patterns:
            matches = re.findall(pattern, result.html, re.IGNORECASE | re.DOTALL)
            if matches:
                print(f"  {desc}: {matches[:5]}")

        # Show all instances of € followed by numbers
        print("\n=== ALL EURO AMOUNTS (first 10) ===")
        all_euros = re.findall(r"€\s*([\d.,]+)", result.html)
        for i, amount in enumerate(all_euros[:10], 1):
            print(f"  {i}. € {amount}")

        print("\n⚠️  Please manually visit the URL and note the correct betriebskosten value")
        print(f"   {url}")
        print("   Then update the test expectations in test_betriebskosten_extraction.py")


if __name__ == "__main__":
    asyncio.run(fetch_fixture())
