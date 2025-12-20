# noessi-crawl

A Python-based web crawler for extracting apartment listings from Austrian real estate portals (Willhaben.at and ImmobilienScout24.at). Built with crawl4ai and Playwright to scrape property data, perform investment analysis, and generate individual markdown reports for each listing.

## Features

- **Multi-portal support**: Scrapes Willhaben.at and ImmobilienScout24.at
- Automated apartment listing scraping with configurable portal selection
- Smart pagination (crawls until no more results found)
- Configurable search parameters (location area IDs, price range)
- Ad filtering (excludes promoted listings)
- **Robust data extraction** with validation:
  - Multi-strategy: JSON-LD → Regex → Optional LLM (improved)
  - **Enhanced LLM extraction** with 5-strategy JSON parsing, HTML preprocessing, 100KB limit
  - **Diagnostic logging** for raw LLM responses (configurable)
  - **Data quality warnings** (NEW - 2025-12-20): Tracks extraction issues, missing fields, rejected values
  - **Betriebskosten post-validation** (NEW - 2025-12-20): Prevents false positives from postal codes, percentages, street addresses
  - Critical field validation: price, size_sqm required; betriebskosten optional with warnings
  - Negative lookbehind patterns reject partial numbers
  - Relaxed LLM validation thresholds (€30+ betriebskosten, €10+ reparaturrücklage)
- **Investment Analysis**:
  - Yield calculations (gross/net)
  - Cash flow projections
  - Investment scoring (0-10 scale)
  - Recommendations (STRONG BUY to AVOID)
  - **NEW: AI-generated investment summaries** (100-150 words, German, optional)
- **Individual markdown files** per apartment with YAML frontmatter and data quality warnings
- **PDF investment reports** with professional styling, clickable navigation, AI summaries, and warning indicators
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
# Then pull a model: ollama pull qwen2.5:14b
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

  "llm_settings": {
    "enabled": true,
    "model": "qwen2.5:14b",
    "html_max_chars": 100000,
    "generate_summary": true,
    "summary_max_words": 150,
    "diagnostics_enabled": false,
    "trigger_mode": "conservative",
    "quality_check_enabled": true,
    "extraction_timeout": 180,
    "summary_timeout": 120,
    "summary_min_words": 80
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
    }
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
| `portal` | string | Portal name: "willhaben" or "immoscout" |
| `postal_codes` | array | List of Austrian postal codes to search (e.g., ["1010", "9020"]) |
| `output_folder` | string | Output directory (default: "output") |
| `max_pages` | number/null | Max pages to scrape (null = unlimited) |

#### LLM Settings

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Enable Ollama LLM for extraction and summaries |
| `model` | string | Ollama model to use (e.g., "qwen2.5:14b") |
| `html_max_chars` | number | Max HTML chars sent to LLM (default: 100000) |
| `generate_summary` | boolean | Generate AI-powered investment summaries |
| `summary_max_words` | number | Max words per summary (default: 150) |
| `summary_min_words` | number | Min words per summary (default: 80) |
| `diagnostics_enabled` | boolean | Enable diagnostic logging and data saving |
| `trigger_mode` | string | When to trigger LLM ("conservative", "aggressive", "always") |
| `quality_check_enabled` | boolean | Enable quality validation of LLM responses |
| `extraction_timeout` | number | Timeout in seconds for LLM extraction (default: 180) |
| `summary_timeout` | number | Timeout in seconds for summary generation (default: 120) |

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

Simply add the postal codes you want to search in the `postal_codes` array in config.json. The scraper automatically translates them to the appropriate portal-specific format.

### Switching Between Portals

To switch between portals, simply change the `portal` field in config.json:

```json
{
  "portal": "willhaben",    // For Willhaben.at
  // or
  "portal": "immoscout",    // For ImmobilienScout24.at
  "postal_codes": ["1010", "1020"]
}
```

**Note**: Each portal has its own URL structure and extraction patterns, but the configuration and output format remain consistent.

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

When `llm_settings.generate_summary: true` in config, each apartment gets an 80-150 word German investment analysis that:
- Synthesizes all data into investment insights
- Balances opportunities and risks
- Provides clear investment perspective
- Appears in PDF after positive/risk factors section
- Generated using Ollama (requires Ollama running locally)
- Quality-checked when `quality_check_enabled: true`

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
| Missing betriebskosten | -1.0 |

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
├── portals/                   # Portal adapter pattern
│   ├── __init__.py            # Factory: get_adapter()
│   ├── base.py                # PortalAdapter abstract base class
│   ├── willhaben/             # Willhaben.at portal
│   │   ├── adapter.py         # WillhabenAdapter implementation
│   │   └── constants.py       # PLZ_TO_AREA_ID, AREA_ID_TO_LOCATION
│   └── immoscout/             # ImmobilienScout24.at portal
│       └── adapter.py         # ImmoscoutAdapter implementation
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
   - Required: size ≥ 10 m², price > 0
   - Optional: betriebskosten (adds warning if missing, -1.0 score penalty)
   - **Betriebskosten post-validation** (NEW - 2025-12-20): Rejects false positives
     - Postal codes (1010, 1020 → rejected)
     - Percentages (20% → rejected)
     - Street addresses (Arndtstraße 50 → rejected)
     - Size measurements (20 m² → rejected)
   - Diagnostic logging shows extracted values for debugging
4. **LLM extraction** (optional, improved): Ollama for missing fields
   - **HTML preprocessing** (strips scripts/styles, 100KB limit)
   - **5-strategy JSON parsing** (handles malformed responses)
   - **Diagnostic logging** (see raw LLM responses when enabled)
   - **Trigger modes**: Conservative (missing critical fields), Aggressive (any missing), Always
   - **Quality validation**: Validates LLM responses for accuracy
   - **Configurable timeouts**: 180s default for extraction
   - Graceful failures - continues without LLM data if unavailable
5. **LLM summary generation** (optional): AI investment analysis
   - Generated after investment scoring completes
   - 80-150 word German summaries
   - Appears in PDF reports after positive/risk factors
   - Configurable timeout (120s default), quality checking enabled
   - Graceful degradation if Ollama unavailable

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

- **Portal Adapter Pattern**: Abstract base class with portal-specific implementations
  - Factory pattern for adapter instantiation
  - 9 required methods per adapter (URL building, extraction, filtering)
  - Portal-agnostic domain logic (~2,000 LOC shared across portals)
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
- **Test coverage**: 79 unit tests covering extraction, validation, portal adapters, and backward compatibility

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
# Run all unit tests (79 tests covering extraction, validation, portals)
uv run pytest tests/ -v

# Test specific modules
uv run pytest tests/test_extraction.py -v              # Regex patterns and validation (18 tests)
uv run pytest tests/test_range_parsing.py -v           # Range detection (15 tests)
uv run pytest tests/test_validation.py -v              # Critical field validation (9 tests)
uv run pytest tests/test_portal_adapters.py -v         # Portal adapter tests (19 tests)
uv run pytest tests/test_backward_compatibility.py -v  # Legacy config tests (10 tests)
uv run pytest tests/test_immoscout_basic.py -v         # Immoscout adapter tests (26 tests)

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
- Pull model if missing: `ollama pull qwen2.5:14b`
- **Enable diagnostic logging**: Set `llm_settings.diagnostics_enabled: true` in config.json
- Check logs for "LLM raw response" to see what the model actually returned
- Try different trigger modes: "conservative" (default), "aggressive", or "always"
- Adjust `extraction_timeout` if LLM responses are slow
- Scraper continues gracefully without LLM data on failures

**LLM extraction quality:**
- **Trigger modes** control when LLM is used:
  - `conservative`: Only when critical fields missing (recommended)
  - `aggressive`: When any fields missing
  - `always`: For every apartment (slow, expensive)
- **Quality checking**: Enable with `quality_check_enabled: true` to validate responses
- **HTML preprocessing** removes bloat (scripts/styles) - up to 100KB sent to LLM
- **5 parsing strategies** handle malformed JSON automatically

**LLM summary generation issues:**
- Check `llm_settings.generate_summary: true` in config.json
- Verify Ollama is running (same as extraction)
- Summaries only generated for **valid apartments** (passed critical field validation)
- Check logs: "LLM summary generated (X chars, Y words)" indicates success
- Adjust `summary_timeout` and `summary_min_words` as needed
- PDFs render correctly with or without summaries

**Monitoring Progress:**
- Logs show detailed progress: "Processing apartment (Total so far: X)"
- Diagnostic logs (when enabled): "LLM raw response", "JSON parsed via strategy X"
- Regex extraction: "Regex extracted size_sqm: ..." for critical fields
- LLM operations: availability checks, extraction attempts, success/failures, summary generation
- Summary generation: "LLM summary generated (X chars, Y words)"

## Portal-Specific Details

### Willhaben.at
- **Status**: Fully functional
- **URL Structure**: Uses area IDs (auto-translated from postal codes)
- **Ad Filtering**: Star icon SVG path detection
- **Data Extraction**: JSON-LD ItemList + regex patterns

### ImmobilienScout24.at
- **Status**: Functional (first implementation - 2025-12-16)
- **URL Structure**:
  - Single postal code: `/regional/{postal_code}/wohnung-kaufen`
  - Multiple postal codes: `/regional/wohnung-kaufen?zipCode=1010,1020`
- **Price Extraction**: `data-testid="primary-price"` attribute with German formatting
- **Known Issues**:
  - May need refinement based on edge cases
  - Price pattern handles "ab" (from) prefix for starting prices
  - All extraction strategies tested with real-world samples

## Limitations

**General:**
- No authentication (public listings only)
- LLM extraction requires local Ollama installation
- Single portal per run (no parallel multi-portal execution yet)

**Willhaben.at:**
- None currently identified

**ImmobilienScout24.at:**
- Betriebskosten rarely available (site limitation) - apartments get warnings, not rejected
- Post-validation prevents false positives (postal codes, percentages, addresses)
- Some listings may have alternative HTML structures not yet captured
- Ad filtering patterns may need expansion

## License

[Add your license here]

## Acknowledgments

Built with [crawl4ai](https://github.com/unclecode/crawl4ai) - A powerful web crawling framework.
