"""Test if star icon filtering works"""

import asyncio

from crawl4ai import *


async def test_star_filtering():
    """Check if the last entry has the star icon"""
    # Test one of the suspect URLs
    url = "https://www.willhaben.at/iad/immobilien/d/neubauprojekt/wien/wien-1050-margareten/-unbefristet-vermieteter-altbau-saniertes-haus-stilfassade-1071480820/"

    async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
        result = await crawler.arun(
            url=url, wait_for="css:main", delay_before_return_html=2.0
        )

        if result.success:
            html = result.html
            star_icon_path = "m12 4 2.09 4.25a1.52 1.52 0 0 0 1.14.82l4.64.64-3.42 3.32"

            has_star = star_icon_path in html
            print(f"URL: {url}")
            print(f"Has star icon: {has_star}")

            # Also check if it's marked as neubauprojekt (new construction project)
            is_neubauprojekt = "/neubauprojekt/" in url
            print(f"Is Neubauprojekt: {is_neubauprojekt}")

            # Search for any ad indicators
            ad_indicators = ["Anzeige", "Werbung", "promoted", "sponsored"]
            for indicator in ad_indicators:
                if indicator.lower() in html.lower():
                    print(f"Contains '{indicator}': True")


if __name__ == "__main__":
    asyncio.run(test_star_filtering())
