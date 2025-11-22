# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**noessi-crawl** is a Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). It features:
- Multi-strategy data extraction (JSON-LD, regex, optional LLM)
- Investment analysis with scoring and recommendations
- Individual markdown files with YAML frontmatter for each listing
- Configurable filtering and analysis parameters

## Development Environment

- **Python Version**: 3.13 (specified in `.python-version`)
- **Package Manager**: uv (standard Python packaging via `pyproject.toml`)
- **Key Dependencies**: 
  - crawl4ai >= 0.7.7 (core crawling framework)
  - playwright >= 1.56.0 (browser automation)
  - httpx >= 0.27.0 (async HTTP for Ollama)
  - pyyaml >= 6.0 (YAML frontmatter generation)

## Setup Commands

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for crawl4ai to work)
playwright install

# Optional: Install Ollama for LLM extraction
# See https://ollama.ai for installation
# Then pull a model: ollama pull qwen3:8b
```

## Running the Apartment Scraper

```bash
# Run the scraper
uv run python main.py
```

Output is generated in `output/apartments/active/` as individual markdown files.

## Project Structure

```
noessi-crawl/
├── main.py                 # EnhancedApartmentScraper main entry point
├── config.json             # Configuration file
├── models/                 # Data models
│   ├── __init__.py
│   ├── apartment.py        # ApartmentListing dataclass (~50 fields)
│   └── constants.py        # Austrian real estate constants
├── utils/                  # Utility modules
│   ├── __init__.py
│   ├── extractors.py       # AustrianRealEstateExtractor (regex patterns)
│   ├── address_parser.py   # AustrianAddressParser
│   └── markdown_generator.py  # MarkdownGenerator
├── llm/                    # LLM integration (optional)
│   ├── __init__.py
│   ├── extractor.py        # OllamaExtractor
│   └── analyzer.py         # InvestmentAnalyzer
├── output/                 # Generated files (gitignored)
│   ├── apartments/
│   │   ├── active/         # Accepted listings
│   │   └── rejected/       # Filtered-out listings
│   └── summary_report.md   # Investment summary
└── tests/                  # Test scripts
```

## Configuration

Edit `config.json` to customize behavior:

### Basic Settings
- `portal`: Portal name (currently only "willhaben" supported)
- `area_ids`: List of postal code area IDs
- `price_max`: Maximum price threshold in euros
- `output_folder`: Output directory (default: "output")
- `max_pages`: Max pages to scrape (null = unlimited)

### Extraction Settings
```json
"extraction": {
  "use_llm": false,           // Enable Ollama LLM extraction
  "llm_model": "qwen3:8b",    // Ollama model to use
  "fallback_to_regex": true   // Use regex if LLM fails
}
```

### Investment Filters
```json
"filters": {
  "min_yield": 3.5,           // Minimum gross yield %
  "max_price": 300000,        // Price cap
  "min_size_sqm": 50,         // Size range
  "max_size_sqm": 120,
  "excluded_districts": [],   // Vienna districts to skip
  "min_investment_score": 5.0 // Minimum score (0-10)
}
```

### Analysis Parameters
```json
"analysis": {
  "mortgage_rate": 3.5,       // Annual rate %
  "down_payment_percent": 30,
  "transaction_cost_percent": 9,
  "estimated_rent_per_sqm": {
    "vienna_inner": 16.0,
    "vienna_outer": 13.0
  }
}
```

## Architecture Notes

### Data Extraction Pipeline

Multi-strategy extraction in priority order:
1. **JSON-LD**: Structured data from script tags (most reliable)
2. **Regex**: Pattern matching for German real estate terminology
3. **LLM**: Ollama extraction for missing fields (optional)

### ApartmentListing Model

The `ApartmentListing` dataclass contains ~50 fields including:
- Core: listing_id, source_url, title, price, size_sqm
- Location: street, district, postal_code, city, state
- Financial: betriebskosten, reparaturrucklage, price_per_sqm
- Features: elevator, balcony, terrace, parking, energy_rating
- Investment: estimated_rent, gross_yield, net_yield, investment_score

### Investment Scoring (0-10 scale)

Balanced scoring with max 10.0:
- Base score: 5.0
- Yield bonus: up to +1.5
- Price vs market: up to +1.0  
- Operating costs: up to +0.5
- Condition: up to +0.5
- Energy: up to +0.5
- Features: up to +0.5
- Cash flow: up to +0.5
- Penalties for poor factors

Recommendations: STRONG BUY (8+), BUY (6.5+), CONSIDER (5+), WEAK (3.5+), AVOID (<3.5)

### Austrian-Specific Features

- Vienna district extraction from postal codes (1030 -> 3rd district)
- Complete Vienna district rent multipliers (1-23)
- MRG (Mietrechtsgesetz) rent control detection for pre-1945 buildings
- German real estate terminology patterns (Betriebskosten, Erstbezug, etc.)
- Transaction cost calculation (Grunderwerbsteuer, Grundbuch, Notar)

### Rate Limiting

Configurable delays to be polite:
- `delay_apartment`: 0.5s between apartment fetches
- `delay_page`: 1.0s between listing pages

### Output Format

Each apartment generates a markdown file with:
- YAML frontmatter (all structured data)
- Investment summary and score
- Financial analysis table
- Property details and features
- Risk/positive factors
- Next steps checklist

## Testing

```bash
# Run existing tests
uv run python tests/test_simple.py
uv run python tests/test_single.py
```
