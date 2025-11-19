"""Simple test to check if we can crawl willhaben.at"""

import asyncio
import json
from pathlib import Path

from crawl4ai import *


async def test_simple_crawl():
    """Test basic crawling without LLM extraction"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    url = config.get("url")
    print(f"Testing crawl of: {url}\n")

    async with AsyncWebCrawler(headless=True, verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            wait_for="css:section",
            delay_before_return_html=3.0,
            js_code="window.scrollTo(0, document.body.scrollHeight);",
        )

        if result.success:
            print(f"\n✅ Crawl successful!")
            print(f"📄 HTML length: {len(result.html)} chars")
            print(f"📝 Markdown length: {len(result.markdown)} chars")

            # Save HTML for inspection
            with open("debug_output.html", "w", encoding="utf-8") as f:
                f.write(result.html)
            print(f"💾 Saved HTML to debug_output.html")

            # Show first part of markdown
            print(f"\n📋 First 500 chars of markdown:")
            print(result.markdown[:500])
        else:
            print(f"❌ Crawl failed: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(test_simple_crawl())
