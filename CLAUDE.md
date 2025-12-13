# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**noessi-crawl** is a Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). It features:
- Multi-strategy data extraction (JSON-LD, regex, enhanced LLM via Ollama)
- **NEW:** Improved LLM extraction (5-strategy JSON parsing, HTML preprocessing, diagnostic logging)
- **NEW:** AI-generated investment summaries (100-150 words, German, optional)
- Investment analysis with scoring (0-10 scale) and buy recommendations
- Individual markdown files with YAML frontmatter for each listing
- Professional PDF reports with clickable navigation, two-column layout, and AI summaries
- Timestamped run folders with top N apartments in `active/`, rest in `rejected/`
- German-language output (field labels, headers, recommendations)
- Austrian-specific features (Vienna districts, MRG detection, postal code mapping)

## Development Environment

- **Python Version**: 3.13 (specified in `.python-version`)
- **Package Manager**: uv (modern Python packaging via `pyproject.toml`)
- **Key Dependencies**:
  - crawl4ai >= 0.7.7 (core crawling framework)
  - playwright >= 1.56.0 (browser automation)
  - httpx >= 0.27.0 (async HTTP for Ollama)
  - pyyaml >= 6.0 (YAML frontmatter generation)
  - fpdf2 >= 2.8.5 (PDF report generation)

## Setup Commands

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for crawl4ai)
playwright install

# Optional: Install Ollama for LLM extraction
# See https://ollama.ai for installation
# Then pull a model: ollama pull qwen3:8b
```

## Running the Scraper

```bash
# Run the apartment scraper
uv run python main.py
```

Output is generated in `output/apartments_YYYY-MM-DD-HHMMSS/` with:
- `active/` - Top N apartments by investment score (default: 20)
- `rejected/` - All other apartments with rejection reason
- `summary_report.md` - Markdown investment summary
- `investment_summary.pdf` - PDF investment report with clickable navigation

## Project Structure

```
noessi-crawl/
├── main.py                        # EnhancedApartmentScraper entry point
├── config.json                    # Configuration (search params, filters, analysis)
├── models/                        # Data models
│   ├── __init__.py
│   ├── apartment.py               # ApartmentListing dataclass (~65 fields)
│   └── constants.py               # Austrian constants (PLZ_TO_AREA_ID, VIENNA_DISTRICTS, etc.)
├── utils/                         # Utility modules
│   ├── __init__.py
│   ├── extractors.py              # AustrianRealEstateExtractor (regex patterns)
│   ├── address_parser.py          # AustrianAddressParser (street, PLZ, city, district)
│   ├── markdown_generator.py      # MarkdownGenerator (individual files with YAML)
│   ├── pdf_generator.py           # PDFGenerator (professional PDF reports)
│   └── translations.py            # German translations (HEADERS, LABELS, RECOMMENDATIONS)
├── llm/                           # LLM integration (optional)
│   ├── __init__.py
│   ├── extractor.py               # OllamaExtractor (enhanced: 5-strategy parsing, HTML preprocessing)
│   ├── summarizer.py              # ApartmentSummarizer (NEW: AI investment summaries)
│   └── analyzer.py                # InvestmentAnalyzer (scoring, yield, cash flow)
├── output/                        # Generated files (gitignored)
│   └── apartments_YYYY-MM-DD-HHMMSS/
│       ├── active/                # Top N apartments
│       ├── rejected/              # Rest of apartments
│       ├── summary_report.md      # Markdown summary
│       └── investment_summary.pdf # PDF report
├── tests/                         # Test scripts
│   ├── test_extraction.py         # Unit tests: regex patterns, validation
│   ├── test_range_parsing.py      # Unit tests: range detection
│   ├── test_validation.py         # Unit tests: critical field validation
│   ├── test_simple.py             # Integration: basic scraping
│   ├── test_single.py             # Integration: single apartment
│   └── test_star_icon.py          # Integration: ad filtering
├── CLAUDE.md                      # This file
└── README.md                      # User documentation
```

## Configuration

Edit `config.json` to customize behavior. Key sections:

### Basic Settings

```json
{
  "portal": "willhaben",           // Currently only willhaben supported
  "postal_codes": ["1010", "9020"], // Postal codes to search (translates to area_ids)
  "price_max": 200000,             // Max price filter for search URL
  "output_folder": "output",       // Output directory
  "max_pages": 1                   // Max pages to scrape (null = unlimited)
}
```

**Important**: Use `postal_codes` (preferred) instead of legacy `area_ids`. The code translates postal codes to willhaben area_ids using `PLZ_TO_AREA_ID` mapping in `models/constants.py`.

### LLM Settings

```json
"llm_settings": {
  "enabled": false,                // Enable Ollama LLM for extraction and summaries
  "model": "qwen3:8b",             // Ollama model name (used for both extraction and summaries)
  "html_max_chars": 50000,         // Max HTML chars to LLM (prevents token overflow)
  "generate_summary": false,       // Generate AI-powered investment summaries
  "summary_max_words": 150,        // Max words per summary (100-150 recommended)
  "diagnostics_enabled": false     // Enable diagnostic logging and data saving
}
```

**LLM Features:**
- **Unified model**: Single model for both data extraction and summary generation
- **HTML preprocessing**: Strips scripts/styles, preserves JSON-LD, 50KB limit
- **5-strategy JSON parsing**: Handles malformed JSON (missing quotes, trailing commas, regex fallback)
- **Diagnostic mode**: When enabled, logs raw LLM responses and saves extraction data to `diagnostics/` folder
- **AI summaries**: 100-150 word German investment summaries synthesizing all data (appears in PDF reports)
- **Graceful degradation**: Scraper continues without LLM data if Ollama unavailable

### Filters

```json
"filters": {
  "min_yield": null,               // Minimum gross yield % (null = disabled)
  "max_price": null,               // Price cap (null = disabled)
  "min_size_sqm": null,            // Size range
  "max_size_sqm": null,
  "excluded_districts": [],        // Vienna districts to skip (e.g., [1, 2, 3])
  "max_betriebskosten_per_sqm": null,  // Max operating costs per m²
  "exclude_renovierung_needed": false, // Skip apartments needing renovation
  "exclude_poor_energy": false,    // Skip poor energy ratings
  "min_investment_score": null     // Minimum score threshold
}
```

**Note**: Filters are defined but not actively applied in current implementation. Apartments are ranked by score, and top N go to `active/`, rest to `rejected/`.

### Analysis Parameters

```json
"analysis": {
  "mortgage_rate": 3.5,            // Annual interest rate %
  "down_payment_percent": 10,      // Down payment %
  "transaction_cost_percent": 9,   // Total transaction costs %
  "loan_term_years": 30,           // Mortgage term
  "estimated_rent_per_sqm": {      // Rent estimates by location
    "default": 12.0,
    "vienna_inner": 16.0,
    "vienna_outer": 13.0,
    "graz": 11.0,
    "linz": 10.5,
    "salzburg": 14.0
  }
}
```

**Note**: LLM-powered investment summaries are now configured in the `llm_settings` section.

### Output Settings

```json
"output": {
  "generate_summary": true,         // Generate summary reports (MD + PDF)
  "pdf_top_n": 20,                  // Number of apartments in active folder
  "generate_pdf": true,             // Generate PDF report (default: true)
  "pdf_filename": "investment_summary.pdf"  // PDF filename
}
```

**Key behavior**: All apartments are ranked by investment score. Top N go to `active/`, rest to `rejected/`. Summary reports (markdown + PDF) only include active apartments. Both reports stay in sync.

### Rate Limiting

```json
"rate_limiting": {
  "delay_apartment": 0.5,          // Seconds between apartment requests
  "delay_page": 1.0                // Seconds between pagination pages
}
```

## Architecture Details

### Main Scraper Flow (main.py)

The `EnhancedApartmentScraper` class orchestrates the entire process:

1. **Initialization**: Load config, translate postal codes to area_ids, initialize components
2. **URL Building**: `build_willhaben_url()` constructs search URL with area_ids and price_max
3. **Page Scraping**: `scrape_page()` fetches listing page, extracts URLs from JSON-LD
4. **Apartment Processing**: `process_apartment()` fetches detail page, extracts data
5. **Multi-strategy Extraction**: JSON-LD → DOM → Regex (with range parsing) → LLM (if enabled)
6. **Critical Field Validation**: Rejects apartments missing price, size_sqm, or betriebskosten_monthly
7. **Investment Analysis**: `InvestmentAnalyzer.analyze_apartment()` calculates metrics and score
8. **Sorting and Saving**: `_save_apartments()` ranks by score, saves top N to active, rest to rejected
9. **Report Generation**: `_generate_summary_report()` and `_generate_pdf_report()` create synchronized reports

### Data Extraction Pipeline

**Priority order**: JSON-LD > Regex > LLM

1. **JSON-LD Extraction** (`_extract_json_ld()`):
   - Looks for `<script type="application/ld+json">` with `"@type": "Product"`
   - Extracts title, price, structured data
   - Most reliable but may miss apartment-specific fields

2. **Regex Extraction** (`AustrianRealEstateExtractor`):
   - **Robust patterns** rejecting common extraction errors:
     - Negative lookbehind `(?<![0-9.,])` prevents matching partial numbers
     - Requires 2+ digits or 1-9 start to reject "0,43 m²" errors
     - Priority: ranges first, then specific digits with m²
   - **German terminology**: Betriebskosten, Reparaturrücklage, Zimmer, m², Stock, Baujahr
   - **Boolean features**: Aufzug (elevator), Balkon, Terrasse, Parkplatz
   - **Range parsing**: Automatically extracts lower value from ranges
     - Patterns: "40-140 m²", "100.000-150.000 EUR", "2,5 bis 3,5 Zimmer"
     - Separators: `-`, `bis`, `~`, `to`
     - Conservative: Always takes lower value for investment analysis
   - **Validation at extraction**: min_value/max_value filters (size: 10-500 m²)

3. **Address Extraction** (`_extract_address_from_html()`):
   - Multiple strategies: JSON-LD address, HTML patterns, URL parsing
   - Parsed by `AustrianAddressParser`: street, house number, PLZ, city, district
   - Vienna district extraction from postal codes (1030 → district 3)

4. **LLM Extraction** (optional, enhanced `OllamaExtractor`):
   - **HTML preprocessing**: Strips scripts/styles, preserves JSON-LD, 50KB limit (was 20KB)
   - **5-strategy JSON parsing**: Direct → markdown block → object → repair → regex fallback
   - **Diagnostic logging**: Logs raw responses when `llm_settings.diagnostics_enabled: true`
   - **Relaxed validation**: €10+ betriebskosten (was €20+), €1+ reparaturrücklage (was €5+)
   - Fills missing fields only, doesn't overwrite existing data
   - Timeout: 10s connect, 120s read, 180s hard limit
   - Graceful failures: Continues without LLM data if unavailable

5. **LLM Summary Generation** (optional, new `ApartmentSummarizer`):
   - Generated after investment analysis completes
   - 100-150 word German summaries synthesizing all data
   - Uses apartment metrics + positive/risk factors
   - Timeout: 90s (shorter than extraction)
   - Appears in PDF after positive/risk factors section

6. **Critical Field Validation** (`_validate_critical_fields()`):
   - Validates after ALL extraction strategies complete (JSON-LD, DOM, Regex, LLM)
   - **Required fields**: price > 0, size_sqm ≥ 10 m², betriebskosten_monthly > 0
   - **Strict size validation**: Minimum 10 m² rejects extraction errors like 0.43 m²
   - Logged rejections at WARNING level with clear reasons
   - Prevents incomplete/invalid data from polluting investment analysis
   - Diagnostic logging: INFO-level logs show extracted size_sqm values for debugging

### Investment Analysis (llm/analyzer.py)

`InvestmentAnalyzer.analyze_apartment()` calculates:

**Financial Metrics**:
- `price_per_sqm`: Price / size_sqm
- `betriebskosten_per_sqm`: Monthly operating costs / size_sqm
- `estimated_rent`: Based on location (Vienna inner/outer, other cities)
- `gross_yield`: (annual rent / price) * 100
- `net_yield`: ((annual rent - annual costs) / price) * 100
- `monthly_cash_flow`: Rent - operating costs - mortgage payment
- `total_investment`: Price + transaction costs (9%)

**Investment Score (0-10 scale)**:
- Base score: 5.0
- Yield bonus: up to +1.5 (for gross_yield > 5.5%)
- Price vs market: up to +1.0 (price_per_sqm below regional average)
- Low operating costs: up to +0.5 (< €2.5/m²)
- Good condition: up to +0.5 (Erstbezug, Saniert, Neuwertig)
- Energy efficiency: up to +0.5 (A, B, C ratings)
- Features: up to +0.5 (elevator, balcony, parking)
- Positive cash flow: up to +0.5
- Penalties for negative factors (high costs, poor energy, old building)

**Recommendations** (German):
- STARK KAUFEN (STRONG BUY): 8.0+ → "Ausgezeichnete Investition"
- KAUFEN (BUY): 6.5-8.0 → "Gute Investition"
- ÜBERLEGEN (CONSIDER): 5.0-6.5 → "Durchschnittliche Investition"
- SCHWACH (WEAK): 3.5-5.0 → "Unterdurchschnittliche Investition"
- VERMEIDEN (AVOID): <3.5 → "Risikoreiche Investition"

### Markdown Generation (utils/markdown_generator.py)

Each apartment gets an individual file: `YYYY-MM-DD_city_district_price.md`

**File Structure**:
1. **YAML Frontmatter**: All structured data (65+ fields)
2. **Investment Summary**: Score, recommendation, key metrics
3. **Financial Analysis Table**: Price, costs, yield, cash flow
4. **Property Details**: Size, rooms, floor, condition, year built
5. **Location**: City, postal code, district, full address
6. **Features**: Elevator, balcony, parking, energy rating
7. **Investment Analysis**: Positive factors, risk factors
8. **Regulatory Notes**: MRG detection for pre-1945 buildings
9. **Next Steps**: Viewing, financing, documentation checklist
10. **Source Link**: Original listing URL

**German Output**: All labels, headers, and text use translations from `utils/translations.py`.

### PDF Generation (utils/pdf_generator.py)

The `PDFGenerator` class creates professional investment reports synchronized with markdown output:

**Page 1 - Summary**:
- Run metadata (timestamp, postal codes, filters)
- Statistics box (total apartments, average score, average yield)
- Investment ranking table with clickable internal links to detail pages
- Color-coded scores (green 8+, blue 6.5-8, yellow 5-6.5, orange 3.5-5, red <3.5)

**Pages 2+ - Apartment Details** (one per page):
- **Two-column layout**: Financial analysis (left) + Property details (right)
- Financial: Price, yield, cash flow, operating costs, recommendation
- Property: Size, rooms, condition, features, location
- Investment analysis: Positive factors and risk factors
- **NEW: AI summary** (if enabled): Appears after risk factors with German investment insights
- Footer with clickable source URL

**Technical Details**:
- Uses NotoSans fonts for German character support (ä, ö, ü, ß)
- Internal links via `add_link()` and `set_link()` for navigation
- Professional navy/gray color scheme suitable for investors
- Outputs to `{run_folder}/investment_summary.pdf`

### Austrian-Specific Features

**Vienna District Handling** (models/constants.py):
- `VIENNA_DISTRICTS`: Mapping of 23 districts with names and rent multipliers
- Postal code → district: 1030 → 3 (Landstraße), 1100 → 10 (Favoriten)
- Rent estimation uses district-specific multipliers (inner districts higher)

**Postal Code to Area ID Translation**:
- `PLZ_TO_AREA_ID`: Maps Austrian postal codes to willhaben area_ids
- Supports Vienna (1010-1230), Graz (8010-8075), Klagenfurt (9020-9073), Villach (9500-9523)
- Legacy support: Can still use `area_ids` directly in config

**MRG Rent Control Detection**:
- Buildings built before 1945 may fall under Mietrechtsgesetz (MRG)
- Affects rental potential and legal obligations
- Noted in markdown output under "Regulatory Notes"

**Transaction Cost Calculation**:
- Grunderwerbsteuer (property transfer tax): 3.5%
- Grundbuchseintragung (land registry): ~1.1%
- Notary/attorney fees: ~1.5-3%
- Real estate agent commission (if applicable): varies
- Default total: 9% in config

**German Terminology Recognition**:
- Betriebskosten (operating costs), Reparaturrücklage (reserve fund)
- Erstbezug (first occupancy), Altbau (old building), Neubau (new building)
- Zimmer (rooms), Stock (floor), Aufzug (elevator), Balkon (balcony)
- Heizungsart (heating type), HWB (heating demand), fGEE (energy efficiency)

### Ad Filtering & Output

- Filters promoted ads by checking star icon SVG path
- Creates timestamped folders: `apartments_YYYY-MM-DD-HHMMSS` (self-contained runs)

### Pagination & Rate Limiting

- Continues until empty pages (consecutive_empty_pages >= 2) or `max_pages` limit
- Rate limits: 0.5s between apartments, 1.0s between pages (configurable)
- Prevents server overload and IP blocking

## ApartmentListing Data Model

The `ApartmentListing` dataclass (models/apartment.py) contains ~65 fields:

**Core Identifiers**:
- listing_id, source_url, source_portal, scraped_at

**Address** (9 fields):
- street, house_number, door_number, district, district_number
- postal_code, city, state, full_address

**Financial** (8 fields):
- price, price_per_sqm, betriebskosten_monthly, betriebskosten_per_sqm
- reparaturrucklage, heating_cost_monthly, total_monthly_cost

**Property Specs** (11 fields):
- title, size_sqm, rooms, bedrooms, bathrooms
- floor, floor_text, total_floors, year_built, year_renovated

**Features** (20+ fields):
- condition, building_type, parking, elevator, balcony, terrace, garden
- cellar, storage, furnished, pets_allowed, accessible
- commission_free, commission_percent

**Energy** (5 fields):
- energy_rating, hwb_value, fgee_value, heating_type

**Investment Metrics** (10+ fields):
- estimated_rent, monthly_cash_flow, gross_yield, net_yield
- investment_score, recommendation, positive_factors, risk_factors
- **NEW:** llm_summary, llm_summary_generated_at

**Metadata**:
- raw_json_ld, description, tags

## Testing

```bash
# Run all unit tests (extraction, validation, range parsing)
uv run pytest tests/ -v

# Test specific modules
uv run pytest tests/test_extraction.py -v      # Regex patterns and validation
uv run pytest tests/test_range_parsing.py -v   # Range detection
uv run pytest tests/test_validation.py -v      # Critical field validation

# Integration tests
uv run python tests/test_simple.py      # Basic scraping
uv run python tests/test_single.py      # Single apartment extraction
uv run python tests/test_star_icon.py   # Ad filtering
```

## Common Development Tasks

### Adding New Postal Codes

Edit `config.json`:
```json
"postal_codes": ["1010", "1020", "9020", "9061"]
```

Or add to `models/constants.py` if not in `PLZ_TO_AREA_ID`:
```python
PLZ_TO_AREA_ID = {
    "1010": 900,  # Vienna 1st district
    # Add new mapping here
}
```

### Modifying Investment Scoring

Edit `llm/analyzer.py`, `_calculate_investment_score()` method:
- Adjust weights for each factor
- Add new scoring criteria
- Modify recommendation thresholds

### Changing Output Format

Edit `utils/markdown_generator.py` for markdown changes:
- Modify `generate_apartment_file()` for structure changes
- Update `_generate_frontmatter()` for YAML fields
- Edit `_generate_markdown_body()` for content sections

Edit `utils/pdf_generator.py` for PDF changes:
- Modify `_draw_summary_table()` for summary page layout
- Update `_draw_two_column_layout()` for apartment detail pages
- Adjust colors in class constants (NAVY, GRAY, COLOR_* for scores)

### Adding New Extraction Patterns

Edit `utils/extractors.py`, `AustrianRealEstateExtractor`:
- **Use negative lookbehind** `(?<![0-9.,])` to prevent matching partial numbers
- **Require 2+ digits** or 1-9 start to avoid leading zeros
- **Add min/max validation** to `extract_field()` calls for numeric fields
- **Test with actual HTML samples** and add unit tests in `tests/test_extraction.py`
- **Pattern priority**: ranges first, then specific patterns, fallbacks last

### Customizing German Translations

Edit `utils/translations.py`:
- HEADERS: Section headings
- LABELS: Field labels
- TABLE_HEADERS: Summary table columns
- RECOMMENDATIONS: Investment recommendation levels
- PHRASES: Common phrases ("n/a", "yes", "no", etc.)

## Known Limitations

- Only supports willhaben.at (hardcoded URL patterns, depends on HTML structure)
- No authentication (public listings only)
- LLM features require local Ollama installation
- Filters not actively enforced (apartments ranked by score instead)
- No duplicate checking across runs

## Troubleshooting

**Too many apartments rejected**:
- Check logs for "Missing critical fields" warnings
- Look for "Regex extracted size_sqm: X m²" in INFO logs
- Common issue: size_sqm < 10 m² indicates extraction error (e.g., "0,43" instead of "43")
- Run unit tests: `uv run pytest tests/test_extraction.py -v`

**Wrong field values** (e.g., price_per_sqm too high):
- Usually caused by size_sqm extraction errors
- Check diagnostic logs: "Regex extracted size_sqm: ..."
- Validate patterns reject leading zeros: `pytest tests/test_extraction.py::TestSizeExtractionPatterns -v`

**"No listings found"**: Check postal_codes in config.json, or max_pages limit

**"Failed to fetch"**: Playwright not installed (`playwright install`) or network issues

**LLM extraction issues**:
- Check Ollama: `curl http://localhost:11434/api/tags`
- Enable `llm_settings.diagnostics_enabled: true` to see raw LLM responses
- Check logs for "JSON parsed via strategy X" to see which parsing worked
- HTML preprocessing now strips bloat (50KB limit vs 20KB before)
- Verify model pulled: `ollama list` then `ollama pull qwen3:8b`
- Hard timeout: 180s prevents indefinite hangs
- Scraper continues gracefully without LLM data on failures

**LLM summary generation**:
- Requires `llm_settings.generate_summary: true`
- Only generated for valid apartments (passed critical field validation)
- Check logs: "LLM summary generated (X chars)" indicates success
- Timeout: 90s (shorter than extraction)
- PDFs render correctly with or without summaries

**Wrong postal codes**: Update PLZ_TO_AREA_ID in models/constants.py
**Missing translations**: Add to utils/translations.py

## Best Practices for Claude Code

- Read existing files before modifying (especially for extraction logic)
- Test regex patterns with actual HTML samples from tests/
- Preserve German translations (don't translate output to English)
- Maintain timestamped folder structure for traceability
- Keep investment scoring balanced (max 10.0 total)
- Don't break YAML frontmatter format (markdown files)
- Respect rate limiting (prevents blocking)
- Update this file when adding major features

## References

- crawl4ai documentation: https://crawl4ai.com
- Playwright Python: https://playwright.dev/python/
- willhaben.at: Target portal (respect robots.txt)
- Austrian real estate regulations: MRG, transaction costs
