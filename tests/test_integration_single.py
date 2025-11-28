"""Integration test: Run scraper on single apartment to verify fixes."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import EnhancedApartmentScraper
from crawl4ai import AsyncWebCrawler


async def test_single_apartment():
    """Test the scraper on the apartment we know has betriebskosten = €395"""

    # URL from our fixture (expected betriebskosten: €395)
    test_url = "https://www.willhaben.at/iad/immobilien/d/eigentumswohnung/kaernten/klagenfurt/lichtdurchflutete-wohnung-mit-kleinem-balkon-2061847835/"

    # Simple config for single apartment test
    config = {
        "portal": "willhaben",
        "postal_codes": ["9020"],
        "price_max": 200000,
        "output_folder": "output_test",
        "max_pages": 1,
        "extraction": {
            "use_llm": False,  # Test regex/DOM extraction first
            "llm_model": "qwen3:8b",
            "fallback_to_regex": True,
            "diagnostic_mode": True,  # Enable to see extraction data
            "diagnostic_output": "diagnostics_test",
        },
        "filters": {},
        "analysis": {
            "mortgage_rate": 3.5,
            "down_payment_percent": 30,
            "transaction_cost_percent": 9,
            "loan_term_years": 25,
            "estimated_rent_per_sqm": {
                "default": 12.0,
            },
        },
        "output": {
            "format": "individual_markdown",
            "include_rejected": False,
            "generate_summary": True,
            "summary_top_n": 20,
            "generate_pdf": False,  # Skip PDF for test
        },
        "rate_limiting": {
            "delay_apartment": 0.5,
            "delay_page": 1.0,
        },
    }

    scraper = EnhancedApartmentScraper(config)

    print("=" * 60)
    print("INTEGRATION TEST: Single Apartment Extraction")
    print("=" * 60)
    print(f"\nTest URL: {test_url}")
    print(f"Expected betriebskosten: €395/month")
    print(f"Diagnostic mode: {config['extraction']['diagnostic_mode']}")
    print()

    async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
        apartment = await scraper.process_apartment(crawler, test_url)

        if apartment:
            print("\n" + "=" * 60)
            print("EXTRACTION RESULTS")
            print("=" * 60)
            print(f"\n✓ Apartment successfully extracted")
            print(f"  Title: {apartment.title}")
            print(f"  Price: EUR {apartment.price:,.0f}" if apartment.price else "  Price: N/A")
            print(f"  Size: {apartment.size_sqm} m²" if apartment.size_sqm else "  Size: N/A")
            print(f"  Location: {apartment.city}")
            print()
            print("=" * 60)
            print("BETRIEBSKOSTEN EXTRACTION")
            print("=" * 60)

            if apartment.betriebskosten_monthly:
                extracted_value = apartment.betriebskosten_monthly
                expected_value = 395.0
                difference = abs(extracted_value - expected_value)
                tolerance = expected_value * 0.1

                print(f"\n✅ Betriebskosten EXTRACTED: EUR {extracted_value:.2f}/month")
                print(f"   Expected value: EUR {expected_value:.2f}/month")
                print(f"   Difference: EUR {difference:.2f}")

                if difference <= tolerance:
                    print(f"\n🎉 SUCCESS! Extracted value matches expected (within 10% tolerance)")
                else:
                    print(f"\n⚠️  WARNING: Difference exceeds 10% tolerance (EUR {tolerance:.2f})")

                if apartment.betriebskosten_per_sqm:
                    print(f"   Per m²: EUR {apartment.betriebskosten_per_sqm:.2f}/m²/month")
            else:
                print(f"\n❌ FAILED: Betriebskosten was NOT extracted")
                print(f"   Value: {apartment.betriebskosten_monthly}")

            print()
            print("=" * 60)
            print("INVESTMENT ANALYSIS")
            print("=" * 60)
            print(f"\n  Investment Score: {apartment.investment_score:.1f}/10")
            print(f"  Recommendation: {apartment.recommendation}")
            print(f"  Gross Yield: {apartment.gross_yield:.2f}%" if apartment.gross_yield else "  Gross Yield: N/A")
            print(f"  Cash Flow: EUR {apartment.cash_flow_monthly:.0f}/month" if apartment.cash_flow_monthly else "  Cash Flow: N/A")

            if apartment.risk_factors:
                print(f"\n  Risk Factors:")
                for risk in apartment.risk_factors:
                    print(f"    - {risk}")

            print()
            if config['extraction']['diagnostic_mode']:
                print("=" * 60)
                print(f"📊 Check diagnostic data in: {config['extraction']['diagnostic_output']}/")
                print("=" * 60)

            return apartment
        else:
            print("\n❌ FAILED: Could not extract apartment data")
            return None


if __name__ == "__main__":
    result = asyncio.run(test_single_apartment())
    sys.exit(0 if result and result.betriebskosten_monthly else 1)
