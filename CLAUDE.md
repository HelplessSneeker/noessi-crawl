# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**noessi-crawl** is a Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). It features:
- Multi-strategy data extraction (JSON-LD, regex, enhanced LLM via Ollama)
- Intelligent LLM extraction with trigger modes, quality checking, and configurable timeouts
- AI-generated investment summaries (80-150 words, German, optional)
- Investment analysis with scoring (0-10 scale) and buy recommendations
- Individual markdown files with YAML frontmatter for each listing
- Professional PDF reports with clickable navigation, two-column layout, and AI summaries
- Timestamped run folders with top N apartments in `active/`, rest in `rejected/`
- German-language output (field labels, headers, recommendations)
- Austrian-specific features (Vienna districts, MRG detection, postal code mapping)

## Development Environment

- **Python Version**: 3.13 (`.python-version`)
- **Package Manager**: uv (`pyproject.toml`)
- **Key Dependencies**:
  - crawl4ai >= 0.7.7 (core crawling)
  - playwright >= 1.56.0 (browser automation)
  - httpx >= 0.27.0 (async HTTP for Ollama)
  - pyyaml >= 6.0 (YAML frontmatter)
  - fpdf2 >= 2.8.5 (PDF generation)

## Setup Commands

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required)
playwright install

# Optional: Install Ollama for LLM features
# See https://ollama.ai
ollama pull qwen2.5:14b
```

## Running the Scraper

```bash
uv run python main.py
```

**Graceful Interrupt**: Press `Ctrl+C` to stop extraction early. The scraper will:
- Stop processing new apartments immediately
- Generate summary with all apartments collected so far
- Create markdown and PDF reports with partial data
- Press `Ctrl+C` twice to force exit without summary

Output: `output/apartments_YYYY-MM-DD-HHMMSS/`
- `active/` - Top N apartments by investment score
- `rejected/` - All other apartments
- `summary_report.md` - Markdown summary
- `investment_summary.pdf` - PDF report

## Project Structure

```
noessi-crawl/
├── main.py                    # EnhancedApartmentScraper entry point
├── config.json                # Configuration
├── portals/                   # Portal adapter pattern (NEW - 2025-12-15)
│   ├── __init__.py            # Factory: get_adapter()
│   ├── base.py                # PortalAdapter abstract base class
│   ├── willhaben/             # Willhaben.at portal
│   │   ├── __init__.py
│   │   ├── adapter.py         # WillhabenAdapter implementation
│   │   └── constants.py       # PLZ_TO_AREA_ID, AREA_ID_TO_LOCATION
│   └── immoscout/             # ImmobilienScout24.at portal (placeholder)
│       ├── __init__.py
│       └── adapter.py         # ImmoscoutAdapter (placeholder)
├── models/
│   ├── apartment.py           # ApartmentListing dataclass (~65 fields)
│   ├── constants.py           # Austrian constants (VIENNA_DISTRICTS, rents, transaction costs)
│   └── metadata.py            # ApartmentMetadata for tracking
├── utils/
│   ├── extractors.py          # AustrianRealEstateExtractor (regex patterns)
│   ├── address_parser.py      # AustrianAddressParser
│   ├── markdown_generator.py  # MarkdownGenerator
│   ├── pdf_generator.py       # PDFGenerator
│   ├── translations.py        # German translations
│   └── top_n_tracker.py       # TopNTracker for active/rejected sorting
├── llm/
│   ├── extractor.py           # OllamaExtractor (5-strategy parsing, quality checks)
│   ├── summarizer.py          # ApartmentSummarizer (AI summaries)
│   └── analyzer.py            # InvestmentAnalyzer (scoring, yield, cash flow)
├── output/                    # Generated files (gitignored)
└── tests/                     # Unit and integration tests
    ├── test_portal_adapters.py           # Portal adapter unit tests (NEW)
    └── test_backward_compatibility.py    # Backward compatibility tests (NEW)
```

## Configuration

Edit `config.json` to customize behavior. Key sections:

### Basic Settings

```json
{
  "portal": "willhaben",
  "postal_codes": ["1010", "9020"],  // Preferred over legacy area_ids
  "output_folder": "output",
  "max_pages": 1                     // null = unlimited
}
```

**Important**: Use `postal_codes` (auto-translates via portal adapters, not in `models/constants.py`).

### LLM Settings

```json
"llm_settings": {
  "enabled": true,                   // Enable LLM for extraction and summaries
  "model": "qwen2.5:14b",            // Ollama model (unified for extraction + summaries)
  "html_max_chars": 100000,          // Max HTML chars to LLM
  "generate_summary": true,          // Generate AI summaries
  "summary_max_words": 150,          // Max words per summary
  "summary_min_words": 80,           // Min words per summary
  "diagnostics_enabled": false,      // Enable diagnostic logging
  "trigger_mode": "conservative",    // "conservative" | "aggressive" | "always"
  "quality_check_enabled": true,     // Validate LLM responses
  "extraction_timeout": 180,         // Timeout for extraction (seconds)
  "summary_timeout": 120             // Timeout for summaries (seconds)
}
```

**LLM Trigger Modes**:
- `conservative`: Only when critical fields missing (recommended, default)
- `aggressive`: When any fields missing
- `always`: For every apartment (slow, expensive)

**LLM Features**:
- **HTML preprocessing**: Strips scripts/styles, preserves JSON-LD, 100KB limit
- **5-strategy JSON parsing**: Direct → markdown block → object → repair → regex fallback
- **Quality validation**: Validates responses when `quality_check_enabled: true`
- **Diagnostic mode**: Logs raw responses when `diagnostics_enabled: true`
- **Graceful degradation**: Continues without LLM data if unavailable

### Filters

```json
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
}
```

**Note**: Filters defined but not actively enforced. Apartments ranked by score, top N → `active/`, rest → `rejected/`.

### Analysis Parameters

```json
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
}
```

### Output Settings

```json
"output": {
  "generate_summary": true,
  "pdf_top_n": 20,
  "generate_pdf": true,
  "pdf_filename": "investment_summary.pdf"
}
```

### Rate Limiting

```json
"rate_limiting": {
  "delay_apartment": 0.5,  // Seconds between apartments
  "delay_page": 1.0        // Seconds between pages
}
```

## Architecture Details

### Portal Adapter Pattern (NEW - 2025-12-15)

The scraper uses the **Portal Adapter Pattern** to support multiple Austrian real estate portals while maintaining clean separation between portal-specific logic and domain logic.

**Key Principle**: Portal adapters handle ONLY portal-specific operations (URL building, HTML extraction patterns, ad filtering). All Austrian real estate domain logic (address parsing, investment analysis, LLM extraction, PDF generation) remains portal-agnostic.

#### PortalAdapter Interface

Abstract base class defining 9 methods each portal must implement:

1. **`get_portal_name() -> str`** - Portal identifier ("willhaben", "immoscout")
2. **`normalize_config(config) -> Dict`** - Translate config to portal format
3. **`build_search_url(page, **kwargs) -> str`** - Build search URL with filters
4. **`extract_listing_urls(html) -> List[Dict]`** - Extract URLs from search results
5. **`extract_listing_id(url) -> str`** - Extract listing ID from URL
6. **`should_filter_ad(html) -> bool`** - Detect promoted/sponsored ads
7. **`extract_address_from_html(html, url) -> Optional[str]`** - Extract raw address
8. **`get_crawler_config() -> Dict`** - Detail page crawler settings (optional override)
9. **`get_search_crawler_config() -> Dict`** - Search page crawler settings (optional override)

#### Current Implementations

**WillhabenAdapter** (`portals/willhaben/adapter.py`):
- Translates postal codes to Willhaben area_ids
- Supports both `postal_codes` (new) and `area_ids` (legacy) config formats
- Filters promoted ads using star icon SVG path detection
- Extracts listing URLs from JSON-LD ItemList format
- Portal-specific constants in `portals/willhaben/constants.py`

**ImmoscoutAdapter** (`portals/immoscout/adapter.py`):
- Placeholder implementation (logs warnings)
- Returns safe defaults (empty lists, None, False)
- Ready for future implementation

#### Factory Pattern

```python
from portals import get_adapter

config = {"portal": "willhaben", "postal_codes": ["1010", "1020"], "filters": {...}}
adapter = get_adapter(config)  # Returns WillhabenAdapter
scraper = EnhancedApartmentScraper(config, adapter)
```

#### Portal-Agnostic Components (~2,000 LOC)

These components work across ANY Austrian portal without modification:
- **Data extraction**: `AustrianRealEstateExtractor`, `OllamaExtractor`, JSON-LD parsing
- **Domain logic**: `AustrianAddressParser`, `InvestmentAnalyzer`, `ApartmentSummarizer`
- **Output**: `MarkdownGenerator`, `PDFGenerator`
- **Models**: `ApartmentListing`, `models/constants.py` (Austrian-specific data)

### Main Scraper Flow (main.py)

`EnhancedApartmentScraper` orchestrates (with dependency injection):

1. **Initialization**: Load config, create portal adapter via factory
2. **URL Building**: Adapter builds search URL with portal-specific parameters
3. **Page Scraping**: Fetches listing pages, adapter extracts URLs
4. **Apartment Processing**: Fetches detail pages, multi-strategy extraction
5. **Critical Field Validation**: Rejects apartments missing price, size_sqm, betriebskosten_monthly
6. **Investment Analysis**: Calculates metrics and score via `InvestmentAnalyzer`
7. **Sorting & Saving**: Ranks by score, top N → active, rest → rejected
8. **Report Generation**: Creates synchronized markdown + PDF reports

### Data Extraction Pipeline

**Priority**: JSON-LD > Regex > LLM

1. **JSON-LD Extraction**: `<script type="application/ld+json">` with `"@type": "Product"`
2. **Regex Extraction** (`AustrianRealEstateExtractor`):
   - Negative lookbehind `(?<![0-9.,])` prevents partial numbers
   - Requires 2+ digits or 1-9 start to reject "0,43 m²" errors
   - Range parsing: "40-140 m²" → extracts lower value (40)
   - German terminology: Betriebskosten, Zimmer, Stock, Baujahr, Aufzug, etc.
   - Validation at extraction: size 10-500 m²
3. **Address Extraction**: JSON-LD address, HTML patterns, URL parsing → `AustrianAddressParser`
4. **LLM Extraction** (optional, `OllamaExtractor`):
   - Triggered based on `trigger_mode` setting
   - HTML preprocessing (strips bloat, 100KB limit)
   - 5-strategy JSON parsing
   - Quality validation when enabled
   - Configurable timeout (default 180s)
   - Fills missing fields only
5. **LLM Summary** (optional, `ApartmentSummarizer`):
   - Generated after investment analysis
   - 80-150 word German summaries
   - Quality-checked when enabled
   - Configurable timeout (default 120s)
6. **Critical Field Validation** (`_validate_critical_fields()`):
   - Required: price > 0, size_sqm ≥ 10 m², betriebskosten_monthly > 0
   - Logged rejections at WARNING level
   - Prevents invalid data from polluting analysis

### Investment Analysis (llm/analyzer.py)

**Financial Metrics**:
- price_per_sqm, betriebskosten_per_sqm
- estimated_rent (location-based)
- gross_yield, net_yield
- monthly_cash_flow (rent - costs - mortgage)
- total_investment (price + 9% transaction costs)

**Investment Score (0-10)**:
- Base: 5.0
- Yield bonus: +1.5 (gross_yield > 5.5%)
- Price vs market: +1.0
- Low operating costs: +0.5
- Good condition: +0.5
- Energy efficiency: +0.5
- Features: +0.5
- Positive cash flow: +0.5
- Penalties for negatives

**Recommendations** (German):
- STARK KAUFEN (8.0+): "Ausgezeichnete Investition"
- KAUFEN (6.5-8.0): "Gute Investition"
- ÜBERLEGEN (5.0-6.5): "Durchschnittliche Investition"
- SCHWACH (3.5-5.0): "Unterdurchschnittliche Investition"
- VERMEIDEN (<3.5): "Risikoreiche Investition"

### Markdown Generation (utils/markdown_generator.py)

Each apartment: `YYYY-MM-DD_city_district_price.md`

**Structure**:
1. YAML Frontmatter (65+ fields)
2. Investment Summary (score, recommendation, key metrics)
3. Financial Analysis Table
4. Property Details
5. Location
6. Features
7. Investment Analysis (positive/risk factors)
8. Regulatory Notes (MRG detection)
9. Next Steps
10. Source Link

### PDF Generation (utils/pdf_generator.py)

**Page 1 - Summary**:
- Run metadata, statistics
- Investment ranking table with clickable links
- Color-coded scores

**Pages 2+ - Apartment Details**:
- Two-column layout (financial | property)
- Investment analysis
- AI summary (if enabled)
- Clickable source URL

**Technical**:
- NotoSans fonts for German characters (ä, ö, ü, ß)
- Internal navigation via `add_link()` and `set_link()`
- Navy/gray color scheme

### Austrian-Specific Features

**Vienna Districts**:
- `VIENNA_DISTRICTS`: 23 districts with names and rent multipliers
- Postal code → district: 1030 → 3 (Landstraße)

**Postal Code to Area ID**:
- `PLZ_TO_AREA_ID`: Maps postal codes to willhaben area_ids
- Vienna (1010-1230), Graz (8010-8075), Klagenfurt (9020-9073), Villach (9500-9523)

**MRG Rent Control**:
- Buildings pre-1945 may fall under Mietrechtsgesetz (MRG)
- Noted in markdown output

**Transaction Costs**:
- Grunderwerbsteuer: 3.5%
- Grundbuchseintragung: ~1.1%
- Notary/attorney: ~1.5-3%
- Default total: 9%

**German Terminology**:
- Betriebskosten, Reparaturrücklage, Erstbezug, Altbau, Neubau
- Zimmer, Stock, Aufzug, Balkon, Heizungsart, HWB, fGEE

### Ad Filtering & Pagination

- Filters promoted ads by star icon SVG path
- Continues until empty pages (consecutive_empty_pages >= 2) or max_pages
- Rate limits: 0.5s between apartments, 1.0s between pages

## ApartmentListing Data Model

`ApartmentListing` dataclass (models/apartment.py, ~65 fields):

**Core**: listing_id, source_url, source_portal, scraped_at
**Address** (9): street, house_number, postal_code, city, district, etc.
**Financial** (8): price, price_per_sqm, betriebskosten_monthly, etc.
**Property** (11): title, size_sqm, rooms, floor, year_built, etc.
**Features** (20+): condition, elevator, balcony, parking, energy_rating, etc.
**Investment** (10+): gross_yield, net_yield, investment_score, recommendation, llm_summary, etc.
**Metadata**: raw_json_ld, description, tags

## Testing

```bash
# All unit tests
uv run pytest tests/ -v

# Portal adapter tests (NEW - 2025-12-15)
uv run pytest tests/test_portal_adapters.py -v           # 19 tests
uv run pytest tests/test_backward_compatibility.py -v    # 10 tests

# Specific modules
uv run pytest tests/test_extraction.py -v      # Regex patterns
uv run pytest tests/test_range_parsing.py -v   # Range detection
uv run pytest tests/test_validation.py -v      # Field validation

# Integration tests
uv run python tests/test_simple.py      # Basic scraping
uv run python tests/test_single.py      # Single apartment
uv run python tests/test_star_icon.py   # Ad filtering
```

**Test Coverage** (as of 2025-12-15):
- Portal adapters: 19 tests (postal codes, URL building, filtering, extraction)
- Backward compatibility: 10 tests (legacy configs, new configs, edge cases)
- Total: 76/79 unit tests passing (96% pass rate)

## Common Development Tasks

### Adding Postal Codes

Edit `config.json`:
```json
"postal_codes": ["1010", "1020", "9020"]
```

Or add to portal-specific constants (`portals/willhaben/constants.py`):
```python
PLZ_TO_AREA_ID = {
    "1010": 201,  # Vienna 1st district
    "1020": 202,  # Vienna 2nd district
    # Add new mapping here
}
```

**Note**: Portal-specific constants have been moved from `models/constants.py` to individual portal adapter folders as of 2025-12-15.

### Modifying Investment Scoring

Edit `llm/analyzer.py`, `_calculate_investment_score()`:
- Adjust weights for each factor
- Add new scoring criteria
- Modify recommendation thresholds

### Changing Output Format

**Markdown**: Edit `utils/markdown_generator.py`
- `generate_apartment_file()` for structure
- `_generate_frontmatter()` for YAML
- `_generate_markdown_body()` for content

**PDF**: Edit `utils/pdf_generator.py`
- `_draw_summary_table()` for summary page
- `_draw_two_column_layout()` for detail pages
- Adjust color constants

### Adding Extraction Patterns

Edit `utils/extractors.py`, `AustrianRealEstateExtractor`:
- Use negative lookbehind `(?<![0-9.,])` to prevent partial matches
- Require 2+ digits or 1-9 start to avoid leading zeros
- Add min/max validation to `extract_field()` calls
- Test with actual HTML samples
- Add unit tests in `tests/test_extraction.py`

### Customizing Translations

Edit `utils/translations.py`:
- HEADERS: Section headings
- LABELS: Field labels
- TABLE_HEADERS: Summary table columns
- RECOMMENDATIONS: Investment levels
- PHRASES: Common phrases

## Known Limitations

- Currently supports willhaben.at only (ImmobilienScout24.at is placeholder)
- No authentication (public listings only)
- LLM requires local Ollama installation
- Filters not actively enforced (ranking-based instead)
- No duplicate checking across runs
- No multi-portal parallel/sequential execution (single portal per run)

## Troubleshooting

**Too many rejections**:
- Check logs for "Missing critical fields"
- Look for "Regex extracted size_sqm: X m²" in INFO logs
- Common: size_sqm < 10 m² indicates extraction error
- Run: `uv run pytest tests/test_extraction.py -v`

**Wrong field values**:
- Usually caused by size_sqm extraction errors
- Check diagnostic logs
- Validate patterns: `pytest tests/test_extraction.py::TestSizeExtractionPatterns -v`

**No listings found**: Check postal_codes or max_pages in config

**Failed to fetch**: Run `playwright install` or check network

**LLM issues**:
- Check Ollama: `curl http://localhost:11434/api/tags`
- Pull model: `ollama pull qwen2.5:14b`
- Enable diagnostics: `llm_settings.diagnostics_enabled: true`
- Try different trigger modes: conservative → aggressive → always
- Adjust timeouts if needed
- Check logs for parsing strategies

**LLM summary issues**:
- Requires `llm_settings.generate_summary: true`
- Only for valid apartments (passed validation)
- Check logs: "LLM summary generated (X chars, Y words)"
- Adjust `summary_timeout` and `summary_min_words` as needed

## Best Practices for Claude Code

- Read files before modifying (especially extraction logic)
- Test regex patterns with actual HTML samples
- Preserve German translations (don't translate to English)
- Maintain timestamped folder structure
- Keep investment scoring balanced (max 10.0)
- Don't break YAML frontmatter format
- Respect rate limiting (prevents blocking)
- Update this file for major features

## References

- crawl4ai: https://crawl4ai.com
- Playwright Python: https://playwright.dev/python/
- willhaben.at: Target portal (respect robots.txt)
- Austrian real estate: MRG, transaction costs
