# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**noessi-crawl** is a Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). It uses crawl4ai with Playwright to scrape property data and generate markdown reports for investment analysis.

## Development Environment

- **Python Version**: 3.13 (specified in `.python-version`)
- **Package Manager**: uv (standard Python packaging via `pyproject.toml`)
- **Key Dependencies**: 
  - crawl4ai >= 0.7.7 (core crawling framework)
  - playwright >= 1.56.0 (browser automation)

## Setup Commands

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for crawl4ai to work)
playwright install
```

## Running the Apartment Scraper

```bash
# Run the scraper (outputs to output/apartments.md)
uv run python main.py
```

The scraper reads configuration from `config.json` and:
1. Builds willhaben.at search URL from config parameters (area_ids, price_max)
2. Crawls paginated listing pages until no more results found
3. Extracts apartment URLs from JSON-LD structured data
4. Fetches individual apartment pages for detailed information
5. Filters out ads (checks for star icon SVG path)
6. Extracts: title, price, square meters, price/m², energy class, location
7. Generates a markdown table in `output/apartments.md`

## Configuration

Edit `config.json` to customize:
- `portal`: Portal name (currently only "willhaben" supported)
- `area_ids`: List of postal code area IDs (e.g., [201, 202, 203] for specific regions)
- `price_max`: Maximum price threshold in euros
- `output_folder`: Folder where apartments.md will be saved (default: "output")
- `max_pages`: Maximum pages to scrape (null = unlimited, stops after 2 consecutive empty pages)

## Project Structure

- `main.py`: Main scraper with async crawling and data extraction
- `config.json`: Configuration file (URL, output folder)
- `output/`: Generated files folder (gitignored)
  - `apartments.md`: Apartment listings table
- `tests/`: Test scripts for debugging extraction logic

## Architecture Notes

### Data Extraction Approach

The scraper uses a multi-phase approach:
1. **URL building**: Constructs willhaben.at search URLs from config parameters (area_ids, price_max)
2. **Pagination**: Automatically crawls multiple pages until 2 consecutive empty pages found
3. **List pages**: Extracts apartment URLs from JSON-LD structured data in search results
4. **Detail pages**: Fetches each apartment page and extracts details using regex patterns

### Key Implementation Details

- **URL construction**: Builds search URLs from `area_ids` (postal codes) and `price_max` parameters
- **Automatic pagination**: Continues scraping pages until no more results (2 consecutive empty pages)
- **Vienna district codes**: Postal codes like 1030 encode district as `(code % 100) / 10` (1030 → 3rd district)
- **Price extraction**: Uses JSON-LD `"price"` field from structured data (more reliable than HTML scraping)
- **Rate limiting**: 0.5 second delay between apartment requests, 1.0 second between pages
- **Async operations**: Built on asyncio with crawl4ai's AsyncWebCrawler
- **Ad filtering**: Excludes promoted listings by checking for star icon SVG in HTML

### LLM Note

Originally designed to use LLM extraction (Ollama/llama2), but the current version uses direct HTML/regex extraction which proved more reliable and faster for structured willhaben.at pages.
