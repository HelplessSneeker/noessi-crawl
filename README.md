# noessi-crawl

A Python-based web crawler for extracting apartment listings from willhaben.at (Austrian real estate portal). Built with crawl4ai and Playwright to scrape property data and generate markdown reports for investment analysis.

## Features

- Automated apartment listing scraping from willhaben.at
- Smart pagination (crawls until no more results found)
- Configurable search parameters (location area IDs, price range)
- Ad filtering (excludes promoted listings)
- Structured data extraction (JSON-LD + HTML parsing)
- Markdown table output with investment metrics
- Price per square meter calculations
- Vienna district detection from postal codes
- Rate-limited requests to be polite to the server

## Requirements

- Python 3.13
- uv package manager
- Playwright browsers (for headless browsing)

## Installation

```bash
# Install dependencies
uv sync

# Install Playwright browsers (required for crawl4ai)
playwright install
```

## Configuration

Edit `config.json` to customize your search:

```json
{
  "portal": "willhaben",
  "area_ids": [201, 202, 117223],
  "price_max": 200000,
  "output_folder": "output",
  "max_pages": null
}
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `portal` | string | Portal name (currently only "willhaben" supported) |
| `area_ids` | array | List of postal code area IDs to search (e.g., [201, 202]) |
| `price_max` | number | Maximum price threshold in euros |
| `output_folder` | string | Output directory for generated files (default: "output") |
| `max_pages` | number/null | Maximum pages to scrape (null = unlimited, stops after 2 consecutive empty pages) |

### Finding Area IDs

Area IDs correspond to postal code regions on willhaben.at. You can find them by:
1. Visiting willhaben.at's apartment search
2. Selecting desired locations in the filter
3. Checking the URL for `areaId=` parameters

Common area IDs:
- Vienna districts: 201 (1st), 202 (2nd), 203 (3rd), etc.
- Other Austrian cities have their own area ID codes

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
5. Filter out promoted ads
6. Generate a markdown report in `output/apartments.md`

### Output

The scraper generates `output/apartments.md` with:
- Search parameters and metadata
- Total listings found
- Table with: Title, Price, m², €/m², Energy Class, Location, Link
- Timestamp and source attribution

Example output format:

```markdown
# Willhaben.at Apartment Investment Opportunities

**Generated:** 2025-11-21 14:30:00
**Portal:** willhaben
**Area IDs (PLZ):** 201, 202, 203
**Max Price:** € 200,000
**Total Listings Found:** 45

## Apartment Listings

| Title | Price | m² | €/m² | Energy Class | Location | Link |
|-------|-------|-----|------|--------------|----------|------|
| Charming 2-room apartment... | € 189.000 | 65 m² | € 2.908/m² | C | Wien, 3. Bezirk | [View](url) |
```

## Project Structure

```
noessi-crawl/
├── main.py              # Main scraper with crawling and extraction logic
├── config.json          # Configuration file (search parameters)
├── pyproject.toml       # Python dependencies and project metadata
├── .python-version      # Python version specification (3.13)
├── output/              # Generated output files (gitignored)
│   └── apartments.md    # Apartment listings report
├── tests/               # Test scripts for debugging
├── CLAUDE.md           # AI assistant guidance for the project
└── README.md           # This file
```

## How It Works

### URL Building

Instead of manually providing a search URL, the scraper constructs it from config parameters:

```python
build_willhaben_url(area_ids=[201, 202], price_max=200000, page=1)
# Returns: https://www.willhaben.at/iad/immobilien/eigentumswohnung/eigentumswohnung-angebote?areaId=201&areaId=202&PRICE_TO=200000&page=1&isNavigation=true
```

### Pagination Logic

The scraper automatically handles pagination:
- Starts at page 1
- Continues until 2 consecutive empty pages detected
- Respects `max_pages` limit if configured
- Adds 1-second delay between pages

### Data Extraction

**Phase 1: List Pages**
- Extracts apartment URLs from JSON-LD structured data
- More reliable than HTML scraping

**Phase 2: Detail Pages**
- Fetches individual apartment pages
- Extracts price from JSON-LD `"price"` field
- Parses HTML/markdown for: title, m², energy class, location
- Calculates price per square meter

**Ad Filtering**
- Checks for star icon SVG path in HTML
- Excludes promoted listings without this marker

**Vienna District Detection**
- Parses postal codes from URLs (e.g., `wien-1030-landstrasse`)
- Extracts district: `(postal_code % 100) / 10` (1030 → 3rd district)

### Rate Limiting

- 0.5 second delay between apartment requests
- 1.0 second delay between pagination pages
- Prevents overwhelming the server

## Technical Details

- **Async operations**: Built on Python's asyncio with crawl4ai's AsyncWebCrawler
- **Headless browser**: Uses Playwright for JavaScript-heavy pages
- **Wait strategies**: CSS selectors and configurable delays for dynamic content
- **Robust extraction**: Combines JSON-LD structured data with regex fallbacks
- **Error handling**: Graceful failures with detailed logging

## Dependencies

Key packages (see `pyproject.toml` for full list):
- `crawl4ai >= 0.7.7` - Core crawling framework
- `playwright >= 1.56.0` - Browser automation for JavaScript rendering

## Development

### Running Tests

```bash
# Test scripts in tests/ directory
uv run python tests/test_extraction.py
```

### Debugging

The scraper includes verbose logging:
- URL being crawled
- HTML length received
- Number of apartments found per page
- Extraction progress for individual listings

## Limitations

- Currently only supports willhaben.at portal
- Requires stable internet connection
- Depends on willhaben.at's HTML structure (may break if site changes)
- No authentication support (public listings only)

## Future Enhancements

Potential improvements:
- Support for additional real estate portals
- Database storage (SQLite, PostgreSQL)
- Price history tracking
- Email notifications for new listings
- Advanced filtering (rooms, year built, etc.)
- Interactive dashboard/UI

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Acknowledgments

Built with [crawl4ai](https://github.com/unclecode/crawl4ai) - A powerful web crawling framework for LLM applications.
