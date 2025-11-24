# noessi-crawl

A Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). Built with crawl4ai and Playwright to scrape property data, perform investment analysis, and generate individual markdown reports for each listing.

## Features

- Automated apartment listing scraping from willhaben.at
- Smart pagination (crawls until no more results found)
- Configurable search parameters (location area IDs, price range)
- Ad filtering (excludes promoted listings)
- Multi-strategy data extraction (JSON-LD, regex patterns, optional LLM)
- **Investment Analysis**:
  - Yield calculations (gross/net)
  - Cash flow projections
  - Investment scoring (0-10 scale)
  - Recommendations (STRONG BUY to AVOID)
- **Individual markdown files** per apartment with YAML frontmatter
- **Timestamped run folders** for each scrape session
- Top N apartments saved to `active/`, rest to `rejected/`
- Summary report with links to apartment files
- Austrian-specific features (Vienna districts, MRG detection)
- Rate-limited requests to be polite to the server

## Requirements

- Python 3.13
- uv package manager
- Playwright browsers (for headless browsing)
- Optional: Ollama (for LLM-based extraction)

## Installation

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for crawl4ai)
playwright install

# Optional: Install Ollama for LLM extraction
# See https://ollama.ai for installation
# Then pull a model: ollama pull qwen3:8b
```

## Configuration

Edit `config.json` to customize your search:

```json
{
  "portal": "willhaben",
  "area_ids": [201, 202, 117223],
  "price_max": 200000,
  "output_folder": "output",
  "max_pages": null,

  "extraction": {
    "use_llm": false,
    "llm_model": "qwen3:8b",
    "fallback_to_regex": true
  },

  "filters": {
    "min_yield": null,
    "max_price": null,
    "min_size_sqm": null,
    "max_size_sqm": null,
    "excluded_districts": [],
    "min_investment_score": null
  },

  "analysis": {
    "mortgage_rate": 3.5,
    "down_payment_percent": 30,
    "transaction_cost_percent": 9,
    "estimated_rent_per_sqm": {
      "vienna_inner": 16.0,
      "vienna_outer": 13.0
    }
  },

  "output": {
    "format": "individual_markdown",
    "include_rejected": false,
    "generate_summary": true,
    "summary_top_n": 20
  },

  "rate_limiting": {
    "delay_apartment": 0.5,
    "delay_page": 1.0
  }
}
```

### Configuration Options

#### Basic Settings

| Field | Type | Description |
|-------|------|-------------|
| `portal` | string | Portal name (currently only "willhaben" supported) |
| `area_ids` | array | List of postal code area IDs to search |
| `price_max` | number | Maximum price threshold in euros |
| `output_folder` | string | Output directory (default: "output") |
| `max_pages` | number/null | Max pages to scrape (null = unlimited) |

#### Extraction Settings

| Field | Type | Description |
|-------|------|-------------|
| `use_llm` | boolean | Enable Ollama LLM extraction for missing fields |
| `llm_model` | string | Ollama model to use (e.g., "qwen3:8b") |
| `fallback_to_regex` | boolean | Use regex if LLM fails |

#### Analysis Settings

| Field | Type | Description |
|-------|------|-------------|
| `mortgage_rate` | number | Annual mortgage rate % for cash flow calculation |
| `down_payment_percent` | number | Down payment % for mortgage calculation |
| `transaction_cost_percent` | number | Total transaction costs % |
| `estimated_rent_per_sqm` | object | Rent estimates by region |

#### Output Settings

| Field | Type | Description |
|-------|------|-------------|
| `summary_top_n` | number | Number of top apartments in active folder (default: 20) |
| `generate_summary` | boolean | Generate summary_report.md |

### Finding Area IDs

Area IDs correspond to postal code regions on willhaben.at:
1. Visit willhaben.at's apartment search
2. Select desired locations in the filter
3. Check the URL for `areaId=` parameters

## Usage

```bash
# Run the scraper
uv run python main.py
```

The scraper will:
1. Build search URL from config parameters
2. Crawl paginated listing pages automatically
3. Extract apartment URLs from structured data
4. Fetch detailed information for each listing
5. Perform investment analysis with scoring
6. Sort by investment score
7. Save top N to `active/`, rest to `rejected/`
8. Generate summary report with links

## Output Structure

Each run creates a timestamped folder:

```
output/
└── apartments_2025-11-22-143052/
    ├── active/                    # Top 20 apartments by score
    │   ├── 2025-11-22_wien_bez3_margareten_180k.md
    │   ├── 2025-11-22_wien_bez10_favoriten_150k.md
    │   └── ...
    ├── rejected/                  # All other apartments
    │   └── ...
    └── summary_report.md          # Investment summary with links
```

### Individual Apartment Files

Each apartment gets its own markdown file with:

**YAML Frontmatter:**
- Listing ID, source URL, scraped timestamp
- Location (city, postal code, district, address)
- Price and costs (purchase price, operating costs, price/m²)
- Property specs (size, rooms, floor, year built, condition)
- Features (elevator, balcony, parking, etc.)
- Energy data (rating, HWB value, heating type)
- Investment metrics (yield, cash flow, score, recommendation)
- Tags for searchability

**Markdown Body:**
- Executive summary
- Financial analysis table
- Property details
- Location with city, postal code, district
- Investment analysis (positive/risk factors)
- Next steps checklist
- Source link

### Summary Report

The `summary_report.md` contains:
- Run metadata (timestamp, run ID, search parameters)
- Total scraped / active / rejected counts
- Table of top N investments with:
  - Score, Recommendation
  - Price, Size, Yield
  - Location (postal code, city, district)
  - Link to details file
  - Link to source listing

## Investment Scoring

Apartments are scored on a 0-10 scale:

| Factor | Max Points |
|--------|------------|
| Base score | 5.0 |
| Yield (>5.5% = +1.5) | +1.5 |
| Price vs market | +1.0 |
| Low operating costs | +0.5 |
| Good condition | +0.5 |
| Energy efficiency | +0.5 |
| Features (elevator, etc.) | +0.5 |
| Positive cash flow | +0.5 |

**Recommendations:**
- STRONG BUY: 8.0+
- BUY: 6.5-8.0
- CONSIDER: 5.0-6.5
- WEAK: 3.5-5.0
- AVOID: <3.5

## Project Structure

```
noessi-crawl/
├── main.py                    # EnhancedApartmentScraper entry point
├── config.json                # Configuration file
├── models/                    # Data models
│   ├── apartment.py           # ApartmentListing dataclass (~65 fields)
│   └── constants.py           # Austrian constants (districts, rates)
├── utils/                     # Utilities
│   ├── extractors.py          # Regex patterns for German real estate
│   ├── address_parser.py      # Austrian address parsing
│   └── markdown_generator.py  # Individual file generation
├── llm/                       # Optional LLM integration
│   ├── extractor.py           # Ollama extraction
│   └── analyzer.py            # Investment analysis
├── output/                    # Generated files (gitignored)
│   └── apartments_YYYY-MM-DD-HHMMSS/
├── tests/                     # Test scripts
├── CLAUDE.md                  # AI assistant guidance
└── README.md                  # This file
```

## How It Works

### Data Extraction Pipeline

1. **JSON-LD** (primary): Extracts structured data from script tags
2. **Regex patterns** (fallback): German real estate terminology
3. **LLM extraction** (optional): Ollama for missing fields
   - Robust timeout handling (10s connect, 120s read, 180s hard timeout)
   - Comprehensive logging for visibility and debugging
   - Graceful failures - continues without LLM data if unavailable

### Austrian-Specific Features

- **Vienna districts**: Extracts from postal codes (1030 → 3rd district)
- **District rent multipliers**: All 23 Vienna districts
- **MRG detection**: Identifies pre-1945 buildings (rent control)
- **German terminology**: Betriebskosten, Erstbezug, Altbau, etc.
- **Transaction costs**: Grunderwerbsteuer, Grundbuch, Notar

### Rate Limiting

- 0.5 second delay between apartment requests
- 1.0 second delay between pagination pages
- Configurable via `rate_limiting` in config

## Technical Details

- **Async operations**: Python asyncio with crawl4ai's AsyncWebCrawler
- **Headless browser**: Playwright for JavaScript rendering
- **Multi-strategy extraction**: JSON-LD → Regex → LLM
- **Error handling**: Graceful failures with comprehensive logging
- **Timeout protection**: Multiple layers prevent indefinite hangs
  - Connect timeout: 10s (Ollama availability checks)
  - Read timeout: 120s (LLM inference time)
  - Hard timeout: 180s (entire LLM operation via asyncio.wait_for)
- **Progress tracking**: Detailed logs show extraction strategy, progress, timing, and errors

## Dependencies

Key packages (see `pyproject.toml`):
- `crawl4ai >= 0.7.7` - Web crawling framework
- `playwright >= 1.56.0` - Browser automation
- `httpx >= 0.27.0` - Async HTTP (for Ollama)
- `pyyaml >= 6.0` - YAML frontmatter

## Troubleshooting

### LLM Extraction Issues

**Scraper hangs when `use_llm: true`:**
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check logs - will show "Checking Ollama availability..." and timeout after 10s if unreachable
- Hard timeout (180s) prevents indefinite hangs
- Look for "Cannot connect to Ollama" or "Ollama timeout" in logs

**LLM extraction fails:**
- Verify Ollama is installed and running
- Check model is available: `ollama list` (should show `qwen3:8b` or your configured model)
- Pull model if missing: `ollama pull qwen3:8b`
- Scraper continues gracefully without LLM data on failures

**Monitoring Progress:**
- Logs show detailed progress: "Processing apartment (Total so far: X)"
- LLM operations logged: availability checks, extraction attempts (1/3, 2/3, 3/3), success/failures
- Timing information helps identify bottlenecks

### Other Issues

**No listings found:**
- Verify `postal_codes` or `area_ids` are correct in config.json
- Check `max_pages` isn't too restrictive

**Failed to fetch pages:**
- Ensure Playwright browsers are installed: `playwright install`
- Check network connectivity

## Limitations

- Currently only supports willhaben.at
- Depends on willhaben.at's HTML structure
- No authentication (public listings only)
- LLM extraction requires local Ollama installation

## License

[Add your license here]

## Acknowledgments

Built with [crawl4ai](https://github.com/unclecode/crawl4ai) - A powerful web crawling framework.
