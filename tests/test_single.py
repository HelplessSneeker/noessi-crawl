"""Test fetching a single apartment to debug extraction"""

import asyncio
import re

from crawl4ai import *


async def test_single_apartment():
    """Fetch one apartment and show what we get"""
    # Use one of the URLs we know exists
    url = "https://www.willhaben.at/iad/immobilien/d/eigentumswohnung/kaernten/klagenfurt/zentrumsnaehe-geraeumige-3-zimmer-wohnung-im-obersten-10-stock-mit-aussicht-1892676275/"

    async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
        result = await crawler.arun(
            url=url, wait_for="css:main", delay_before_return_html=2.0
        )

        if result.success:
            print("✅ Crawl successful\n")

            # Save HTML for inspection
            with open("single_apartment.html", "w", encoding="utf-8") as f:
                f.write(result.html)
            print("Saved HTML to single_apartment.html\n")

            html = result.html

            # Try to find price
            print("=== SEARCHING FOR PRICE ===")
            price_patterns = [
                r"(\d+(?:\.\d+)*(?:,\d+)?)\s*€",
                r'"price"[:\s]*"?(\d+(?:\.\d+)*)"?',
                r"Preis[:\s]*(\d+(?:\.\d+)*)",
            ]
            for pattern in price_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    print(f"Pattern '{pattern}' found: {matches[:5]}")

            # Try to find square meters
            print("\n=== SEARCHING FOR SQUARE METERS ===")
            sqm_patterns = [
                r"(\d+(?:,\d+)?)\s*m²",
                r'"area"[:\s]*"?(\d+(?:,\d+)?)"?',
            ]
            for pattern in sqm_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    print(f"Pattern '{pattern}' found: {matches[:5]}")

            # Show first 2000 chars of markdown
            print("\n=== MARKDOWN PREVIEW ===")
            print(result.markdown[:2000])


if __name__ == "__main__":
    asyncio.run(test_single_apartment())
