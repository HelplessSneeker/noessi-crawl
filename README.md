# noessi-crawl

A Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). Built with crawl4ai and Playwright to scrape property data, perform investment analysis, and generate individual markdown reports for each listing.

## Features

- Automated apartment listing scraping from willhaben.at
- Smart pagination (crawls until no more results found)
- Configurable search parameters (location area IDs, price range)
- Ad filtering (excludes promoted listings)
- **Robust data extraction** with validation:
  - Multi-strategy: JSON-LD → Regex → Optional LLM (improved)
  - **NEW: Enhanced LLM extraction** with 5-strategy JSON parsing, HTML preprocessing, 50KB limit
  - **NEW: Diagnostic logging** for raw LLM responses (configurable)
  - Strict validation (size ≥ 10 m²) prevents extraction errors
  - Negative lookbehind patterns reject partial numbers
  - Relaxed LLM validation thresholds (€10+ betriebskosten, €1+ reparaturrücklage)
- **Investment Analysis**:
  - Yield calculations (gross/net)
  - Cash flow projections
  - Investment scoring (0-10 scale)
  - Recommendations (STRONG BUY to AVOID)
  - **NEW: AI-generated investment summaries** (100-150 words, German, optional)
- **Individual markdown files** per apartment with YAML frontmatter
- **PDF investment reports** with professional styling, clickable navigation, and AI summaries
- **Timestamped run folders** for each scrape session
- Top N apartments saved to `active/`, rest to `rejected/`
- Summary report (markdown + PDF) with links to apartment files
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
uv run playwright install

# Optional: Install Ollama for LLM extraction
# See https://ollama.ai for installation
# Then pull a model: ollama pull qwen3:8b
```

## Configuration

Edit `config.json` to customize your search:

```json
{
  "portal": "willhaben",
  "postal_codes": [
    "1010",
    "1020",
    "9020",
    "9061"
  ],
  "output_folder": "output",
  "max_pages": 1,

  "extraction": {
    "use_llm": true,
    "llm_model": "qwen3:8b",
    "fallback_to_regex": true,
    "diagnostic_mode": false,
    "diagnostic_output": "diagnostics",
    "diagnostic_logging": true,
    "html_max_chars": 50000
  },

  "filters": {
    "min_yield": null,
    "max_price": 150000,
    "min_size_sqm": null,
    "max_size_sqm": null,
    "excluded_districts": [],
    "max_betriebskosten_per_sqm": null,
    "exclude_renovierung_needed": false,
    "exclude_poor_energy": false,
    "min_investment_score": null
  },

  "analysis": {
    "mortgage_rate": 3.5,
    "down_payment_percent": 10,
    "transaction_cost_percent": 9,
    "loan_term_years": 30,
    "estimated_rent_per_sqm": {
      "default": 12.0,
      "vienna_inner": 16.0,
      "vienna_outer": 13.0,
      "graz": 11.0,
      "linz": 10.5,
      "salzburg": 14.0
    },
    "generate_llm_summary": true,
    "llm_summary_model": "qwen3:8b",
    "llm_summary_max_words": 150
  },

  "output": {
    "format": "individual_markdown",
    "generate_summary": true,
    "pdf_top_n": 20,
    "generate_pdf": true,
    "pdf_filename": "investment_summary.pdf"
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
| `postal_codes` | array | List of Austrian postal codes to search (e.g., ["1010", "9020"]) |
| `output_folder` | string | Output directory (default: "output") |
| `max_pages` | number/null | Max pages to scrape (null = unlimited) |

#### Extraction Settings

| Field | Type | Description |
|-------|------|-------------|
| `use_llm` | boolean | Enable Ollama LLM extraction for missing fields |
| `llm_model` | string | Ollama model to use (e.g., "qwen3:8b") |
| `fallback_to_regex` | boolean | Use regex if LLM fails |
| `diagnostic_mode` | boolean | Save diagnostic HTML files for troubleshooting |
| `diagnostic_output` | string | Directory for diagnostic files (default: "diagnostics") |
| `diagnostic_logging` | boolean | **NEW:** Enable detailed logging of raw LLM responses |
| `html_max_chars` | number | **NEW:** Max HTML chars sent to LLM (default: 50000, was 20000) |

#### Filter Settings

| Field | Type | Description |
|-------|------|-------------|
| `min_yield` | number/null | Minimum gross yield % threshold |
| `max_price` | number/null | Maximum price filter in euros |
| `min_size_sqm` | number/null | Minimum apartment size in m² |
| `max_size_sqm` | number/null | Maximum apartment size in m² |
| `excluded_districts` | array | Vienna districts to exclude (e.g., [1, 2, 3]) |
| `max_betriebskosten_per_sqm` | number/null | Max operating costs per m² |
| `exclude_renovierung_needed` | boolean | Exclude apartments needing renovation |
| `exclude_poor_energy` | boolean | Exclude poor energy ratings |
| `min_investment_score` | number/null | Minimum investment score threshold |

#### Analysis Settings

| Field | Type | Description |
|-------|------|-------------|
| `mortgage_rate` | number | Annual mortgage rate % for cash flow calculation |
| `down_payment_percent` | number | Down payment % for mortgage calculation |
| `transaction_cost_percent` | number | Total transaction costs % (default: 9%) |
| `loan_term_years` | number | Mortgage loan term in years |
| `estimated_rent_per_sqm` | object | Rent estimates by region (€/m²/month) |
| `generate_llm_summary` | boolean | **NEW:** Generate AI investment summaries for PDF |
| `llm_summary_model` | string | **NEW:** Model for summaries (default: "qwen3:8b") |
| `llm_summary_max_words` | number | **NEW:** Max words per summary (default: 150) |

#### Output Settings

| Field | Type | Description |
|-------|------|-------------|
| `format` | string | Output format ("individual_markdown") |
| `generate_summary` | boolean | Generate summary reports (markdown + PDF) |
| `pdf_top_n` | number | Number of top apartments in active folder (default: 20) |
| `generate_pdf` | boolean | Generate PDF investment report (default: true) |
| `pdf_filename` | string | PDF filename (default: "investment_summary.pdf") |

### Using Postal Codes

The scraper now uses Austrian postal codes directly (no need to find area IDs):

**Supported Cities:**
- **Vienna**: 1010-1230 (all 23 districts)
- **Graz**: 8010-8075
- **Klagenfurt**: 9020-9073
- **Villach**: 9500-9523

Simply add the postal codes you want to search in the `postal_codes` array in config.json. The scraper automatically translates them to willhaben area IDs.

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
    ├── summary_report.md          # Markdown investment summary
    └── investment_summary.pdf     # PDF investment report
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

### Summary Report (Markdown)

The `summary_report.md` contains:
- Run metadata (timestamp, run ID, search parameters)
- Total scraped / active / rejected counts
- Table of top N investments with:
  - Score, Recommendation
  - Price, Size, Yield
  - Location (postal code, city, district)
  - Link to details file
  - Link to source listing

### Investment Report (PDF)

The `investment_summary.pdf` provides a professional report with:
- **Page 1 - Summary**: Run metadata, statistics, clickable ranking table
- **Pages 2+ - Apartment Details** (one per page):
  - Two-column layout (financial analysis + property details)
  - Color-coded investment scores
  - Positive factors and risk factors
  - **NEW: AI-generated investment summary** (if enabled, appears after risk factors)
  - Clickable source URLs
- **Professional styling**: Navy/gray color scheme suitable for investors
- **Internal navigation**: Click apartment rows in summary to jump to detail pages

#### LLM-Generated Summaries

When `generate_llm_summary: true` in config, each apartment gets a 100-150 word German investment analysis that:
- Synthesizes all data into investment insights
- Balances opportunities and risks
- Provides clear investment perspective
- Appears in PDF after positive/risk factors section
- Generated using Ollama (requires Ollama running locally)

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
│   ├── markdown_generator.py  # Individual file generation
│   ├── pdf_generator.py       # PDF report generation
│   └── translations.py        # German translations
├── llm/                       # Optional LLM integration
│   ├── extractor.py           # Ollama extraction (improved)
│   ├── summarizer.py          # AI summary generation (NEW)
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
2. **Regex patterns** (robust fallback):
   - Negative lookbehind prevents matching partial numbers (rejects "0,43 m²")
   - Requires 2+ digits or 1-9 start to avoid leading zeros
   - Min/max validation at extraction (size: 10-500 m²)
   - Range detection with conservative lower-bound extraction
3. **Critical field validation**:
   - Strict minimums: size ≥ 10 m², price > 0, costs > 0
   - Diagnostic logging shows extracted values for debugging
4. **LLM extraction** (optional, improved): Ollama for missing fields
   - **NEW: Enhanced HTML preprocessing** (strips scripts/styles, 50KB limit)
   - **NEW: 5-strategy JSON parsing** (handles malformed responses)
   - **NEW: Diagnostic logging** (see raw LLM responses when enabled)
   - **NEW: Relaxed validation** (€10+ betriebskosten, €1+ reparaturrücklage)
   - Robust timeout handling (10s connect, 120s read, 180s hard timeout)
   - Graceful failures - continues without LLM data if unavailable
5. **LLM summary generation** (optional, new): AI investment analysis
   - Generated after investment scoring completes
   - 100-150 word German summaries
   - Appears in PDF reports after positive/risk factors
   - 60s timeout, graceful degradation if Ollama unavailable

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
- **Multi-strategy extraction**: JSON-LD → Regex (robust patterns) → LLM
- **Validation layers**:
  - Pattern-level: Negative lookbehind, digit requirements
  - Extraction-level: min/max value filters (10-500 m²)
  - Post-extraction: Critical field validation with strict minimums
- **Error handling**: Graceful failures with comprehensive logging
- **Timeout protection**: Multiple layers prevent indefinite hangs
  - Connect timeout: 10s (Ollama availability checks)
  - Read timeout: 120s (LLM inference time)
  - Hard timeout: 180s (entire LLM operation via asyncio.wait_for)
- **Diagnostic logging**: INFO-level logs for extracted values, helpful for troubleshooting
- **Test coverage**: 42 unit tests covering extraction, validation, range parsing

## Dependencies

Key packages (see `pyproject.toml`):
- `crawl4ai >= 0.7.7` - Web crawling framework
- `playwright >= 1.56.0` - Browser automation
- `httpx >= 0.27.0` - Async HTTP (for Ollama)
- `pyyaml >= 6.0` - YAML frontmatter
- `fpdf2 >= 2.8.5` - PDF generation
- `pytest >= 9.0.1` - Testing framework

## Testing

```bash
# Run all unit tests (42 tests covering extraction, validation, range parsing)
uv run pytest tests/ -v

# Test specific modules
uv run pytest tests/test_extraction.py -v      # Regex patterns and validation (18 tests)
uv run pytest tests/test_range_parsing.py -v   # Range detection (15 tests)
uv run pytest tests/test_validation.py -v      # Critical field validation (9 tests)

# Integration tests
uv run python tests/test_simple.py      # Basic scraping functionality
uv run python tests/test_single.py      # Single apartment extraction
uv run python tests/test_star_icon.py   # Ad filtering (star icon detection)
```

## Troubleshooting

### Extraction Issues

**Too many apartments rejected:**
- Check logs for "Missing critical fields: ..." warnings
- Look for "Regex extracted size_sqm: X m²" in INFO logs
- Common cause: size_sqm < 10 m² indicates extraction error (e.g., "0.43" instead of "43")
- Run tests to validate patterns: `uv run pytest tests/test_extraction.py -v`

**Wrong field values (e.g., absurd price_per_sqm):**
- Usually caused by size_sqm extraction errors
- Check diagnostic logs for "Regex extracted size_sqm: ..."
- Example: 0.43 m² instead of 43 m² → price_per_sqm = €313,953 instead of €3,140
- Validate patterns work: `uv run pytest tests/test_extraction.py::TestSizeExtractionPatterns -v`

**No listings found:**
- Verify `postal_codes` or `area_ids` are correct in config.json
- Check `max_pages` isn't too restrictive

**Failed to fetch pages:**
- Ensure Playwright browsers are installed: `uv run playwright install`
- Check network connectivity

### LLM Extraction Issues

**Scraper hangs when `use_llm: true`:**
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check logs - will show "Checking Ollama availability..." and timeout after 10s if unreachable
- Hard timeout (180s) prevents indefinite hangs

**LLM extraction fails or returns no data:**
- Verify Ollama is installed and running: `ollama list`
- Pull model if missing: `ollama pull qwen3:8b`
- **Enable diagnostic logging**: Set `diagnostic_logging: true` in config.json
- Check logs for "LLM raw response" to see what the model actually returned
- Try different parsing strategies (automatically attempted)
- Scraper continues gracefully without LLM data on failures

**LLM extraction improves after update:**
- **HTML preprocessing** now removes bloat (scripts/styles) - more useful data sent to LLM
- **50KB limit** (was 20KB) - captures more complete property specifications
- **5 parsing strategies** handle malformed JSON better
- **Relaxed validation** accepts realistic low-cost apartments (€10+ instead of €20+)

**LLM summary generation issues:**
- Check `generate_llm_summary: true` in config.json under `analysis` section
- Verify Ollama is running (same as extraction)
- Summaries only generated for **valid apartments** (passed critical field validation)
- Check logs: "LLM summary generated (X chars)" indicates success
- Timeout is 90s (shorter than extraction) - check logs for timeout warnings
- PDFs render correctly with or without summaries

**Monitoring Progress:**
- Logs show detailed progress: "Processing apartment (Total so far: X)"
- Diagnostic logs (when enabled): "LLM raw response", "JSON parsed via strategy X"
- Regex extraction: "Regex extracted size_sqm: ..." for critical fields
- LLM operations: availability checks, extraction attempts, success/failures, summary generation
- Summary generation: "LLM summary generated (X chars, Y words)"

## Limitations

- Currently only supports willhaben.at
- Depends on willhaben.at's HTML structure
- No authentication (public listings only)
- LLM extraction requires local Ollama installation

## License

[Add your license here]

## Acknowledgments

Built with [crawl4ai](https://github.com/unclecode/crawl4ai) - A powerful web crawling framework.
