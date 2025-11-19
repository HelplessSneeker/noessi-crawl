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

The scraper reads the search URL from `config.json` and:
1. Fetches the listing page from willhaben.at
2. Extracts apartment URLs from JSON-LD structured data
3. Crawls individual apartment pages (first 30 by default)
4. Filters out ads (checks for star icon SVG path)
5. Extracts: title, price, square meters, price/m², energy class, location
6. Generates a markdown table in `output/apartments.md`

## Configuration

Edit `config.json` to customize:
- `url`: willhaben.at search URL with desired filters (location, price range, etc.)
- `output_folder`: folder where apartments.md will be saved (default: "output")

## Project Structure

- `main.py`: Main scraper with async crawling and data extraction
- `config.json`: Configuration file (URL, output folder)
- `output/`: Generated files folder (gitignored)
  - `apartments.md`: Apartment listings table
- `tests/`: Test scripts for debugging extraction logic

## Architecture Notes

### Data Extraction Approach

The scraper uses a two-phase approach:
1. **List page**: Extracts apartment URLs from JSON-LD structured data in the search results
2. **Detail pages**: Fetches each apartment page and extracts details using regex patterns

### Key Implementation Details

- **Vienna district codes**: Postal codes like 1030 encode district as `(code % 100) / 10` (1030 → 3rd district)
- **Price extraction**: Uses JSON-LD `"price"` field from structured data (more reliable than HTML scraping)
- **Rate limiting**: 0.5 second delay between requests to be polite to the server
- **Async operations**: Built on asyncio with crawl4ai's AsyncWebCrawler

### LLM Note

Originally designed to use LLM extraction (Ollama/llama2), but the current version uses direct HTML/regex extraction which proved more reliable and faster for structured willhaben.at pages.
