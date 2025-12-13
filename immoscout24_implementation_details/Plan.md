# Multi-Portal Web Scraper Implementation Plan

## Overview

This document outlines the implementation plan for expanding the noessi-crawl web scraper to support multiple Austrian real estate portals (Willhaben and ImmobilienScout24) using the Portal Adapter Pattern.

**Current Status**: Documentation phase - planning multi-session implementation

**Target Architecture**: Portal Adapter Pattern with dependency injection

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Current System Analysis](#current-system-analysis)
3. [Implementation Phases](#implementation-phases)
4. [Configuration Design](#configuration-design)
5. [Execution Strategy Analysis](#execution-strategy-analysis)
6. [Critical Files Reference](#critical-files-reference)
7. [Risk Mitigation](#risk-mitigation)
8. [Success Criteria](#success-criteria)

---

## Architecture Overview

### Portal Adapter Pattern

The core abstraction is a `PortalAdapter` base class that defines the interface for portal-specific functionality. Each portal (Willhaben, ImmobilienScout24) implements this interface.

**Key Principle**: Portal adapters handle ONLY portal-specific logic. All Austrian real estate domain logic (address parsing, investment analysis, LLM extraction) remains portal-agnostic and reusable.

### Folder Structure

```
portals/
├── __init__.py                 # Factory function: get_adapter()
├── base.py                     # PortalAdapter abstract base class
├── willhaben/
│   ├── __init__.py
│   ├── adapter.py              # WillhabenAdapter implementation
│   └── constants.py            # PLZ_TO_AREA_ID, AREA_ID_TO_LOCATION
├── immoscout/
│   ├── __init__.py
│   ├── adapter.py              # ImmoscoutAdapter (research + implementation)
│   └── constants.py            # Immoscout-specific mappings (TBD)
└── multi_portal.py             # MultiPortalAdapter for sequential execution
```

### PortalAdapter Interface

Abstract methods that each portal must implement:

1. **`get_portal_name() -> str`**
   - Return portal identifier ("willhaben", "immoscout")

2. **`normalize_config(config: Dict) -> Dict`**
   - Translate portal-agnostic config to portal-specific format
   - Example: postal_codes → area_ids for Willhaben

3. **`build_search_url(page: int, **kwargs) -> str`**
   - Build search URL with filters and pagination
   - Portal-specific URL structure and parameter names

4. **`extract_listing_urls(html: str) -> List[Dict[str, str]]`**
   - Extract apartment URLs from search results page
   - May use JSON-LD, CSS selectors, or regex

5. **`extract_listing_id(url: str) -> str`**
   - Extract unique listing ID from apartment URL
   - Portal-specific URL patterns

6. **`should_filter_ad(html: str) -> bool`**
   - Determine if listing is a promoted ad to filter
   - Portal-specific ad indicators

7. **`extract_address_from_html(html: str, url: str) -> Optional[str]`**
   - Extract raw address text from HTML/URL
   - Portal-specific patterns (actual parsing done by AustrianAddressParser)

8. **`get_crawler_config() -> Dict`** (optional override)
   - Portal-specific crawler settings (wait selectors, delays)

9. **`get_search_crawler_config() -> Dict`** (optional override)
   - Portal-specific settings for search results pages

### What Remains Portal-Agnostic

These components require **ZERO changes** and work across any Austrian portal:

- **Data extraction**:
  - `AustrianRealEstateExtractor` - German terminology regex patterns
  - `OllamaExtractor` - LLM-based extraction
  - JSON-LD extraction (standard schema.org format)

- **Domain logic**:
  - `AustrianAddressParser` - Austrian address format parsing
  - `InvestmentAnalyzer` - Austrian financial models (9% transaction costs, rent estimates)
  - `ApartmentListing` - Core data model

- **Austrian constants**:
  - `VIENNA_DISTRICTS` - 23 districts with rent multipliers
  - `RENT_PER_SQM_DEFAULTS` - Location-based rent estimates
  - `MRG_BUILDING_CUTOFF_YEAR` - Rent control regulations
  - `TRANSACTION_COSTS` - Austrian real estate transaction costs

- **Output generation**:
  - `MarkdownGenerator` - YAML frontmatter + markdown files
  - `PDFGenerator` - Investment summary reports
  - German translations

---

## Current System Analysis

### Willhaben-Specific Coupling Points

The current codebase has tight coupling to Willhaben in these locations:

| File | Lines | Component | Coupling Type |
|------|-------|-----------|---------------|
| `main.py` | 179-198 | `build_willhaben_url()` | Hardcoded base URL + areaId parameters |
| `main.py` | 200-218 | `extract_listing_urls()` | JSON-LD ItemList assumption |
| `main.py` | 220-227 | `extract_listing_id()` | Numeric suffix regex `/(\d+)/?$` |
| `main.py` | 242 | Ad filtering | Star icon SVG path detection |
| `main.py` | 838-913 | `_extract_address_from_html()` | URL patterns `/wien-1030-landstrasse/` |
| `main.py` | 152-177 | `_translate_postal_codes_to_area_ids()` | PLZ_TO_AREA_ID mapping |
| `models/constants.py` | 248-289 | `PLZ_TO_AREA_ID` | Willhaben area ID system |
| `models/constants.py` | 194-244 | `AREA_ID_TO_LOCATION` | Reverse lookup mapping |

**Total Willhaben-specific code**: ~270 lines (to be extracted into WillhabenAdapter)

### Expected Differences: Willhaben vs ImmobilienScout24

| Aspect | Willhaben | ImmobilienScout24 (Expected) |
|--------|-----------|------------------------------|
| **URL Structure** | `/iad/immobilien/.../angebote?areaId=X` | `/regional/{city}/wohnung-kaufen` or `/suche?postcodes=X` (TBD) |
| **Listing IDs** | Numeric suffix in URL | Possibly `/expose/{id}` or similar (TBD) |
| **Search Results** | JSON-LD ItemList | May use JSON-LD or data-* attributes (TBD) |
| **Ad Filtering** | Star icon SVG path presence | CSS class or data attribute (TBD) |
| **Address Format** | Often in URL path (`/wien-1030-landstrasse/`) | Likely only in HTML/JSON-LD (TBD) |
| **Postal Codes** | Translated to internal area_ids | May support direct postal code filtering (TBD) |
| **Pagination** | `?page=1` parameter | Could be `page`, `pagenumber`, or offset-based (TBD) |

Items marked "TBD" require research during Phase 4.

---

## Implementation Phases

### Phase 1: Foundation (Portal Adapter Infrastructure) - 4 hours

**Goal**: Create adapter pattern without breaking existing Willhaben functionality

#### Tasks

1. **Create folder structure**:
   ```bash
   mkdir -p portals/willhaben portals/immoscout
   touch portals/{__init__,base}.py
   touch portals/willhaben/{__init__,adapter,constants}.py
   touch portals/immoscout/{__init__,adapter,constants}.py
   ```

2. **Implement `portals/base.py`**:
   - Abstract `PortalAdapter` class
   - Define all 9 abstract methods
   - Comprehensive docstrings with examples

3. **Implement `portals/willhaben/adapter.py`**:
   - Extract logic from `main.py`:
     - `_translate_postal_codes_to_area_ids()` → constructor
     - `build_willhaben_url()` → `build_search_url()`
     - `extract_listing_urls()` → `extract_listing_urls()`
     - `extract_listing_id()` → `extract_listing_id()`
     - Star icon filtering → `should_filter_ad()`
     - `_extract_address_from_html()` → `extract_address_from_html()`
   - Expected LOC: ~200

4. **Move constants**:
   - `models/constants.py` lines 248-289 → `portals/willhaben/constants.py`
   - Keep in `models/constants.py` temporarily for backward compatibility

5. **Create factory function** (`portals/__init__.py`):
   ```python
   def get_adapter(config: Dict[str, Any]) -> PortalAdapter:
       portal = config.get("portal", "willhaben").lower()
       if portal == "willhaben":
           from portals.willhaben.adapter import WillhabenAdapter
           return WillhabenAdapter(config)
       elif portal == "immoscout":
           from portals.immoscout.adapter import ImmoscoutAdapter
           return ImmoscoutAdapter(config)
       elif portal == "both":
           from portals.multi_portal import MultiPortalAdapter
           return MultiPortalAdapter(config)
       else:
           raise ValueError(f"Unsupported portal: {portal}")
   ```

#### Validation

```bash
python -c "from portals import get_adapter; adapter = get_adapter({'portal': 'willhaben', 'postal_codes': ['1010'], 'filters': {}}); print(adapter.build_search_url())"
```

Expected output: Willhaben search URL with areaId=201

---

### Phase 2: Main.py Integration (Dependency Injection) - 3 hours

**Goal**: Refactor `main.py` to use portal adapters via dependency injection

#### Critical Changes

**File**: `/home/bfn/Documents/workspace/noessi-crawl/main.py`

1. **Constructor** (lines 41-49):
   - Add `portal_adapter: PortalAdapter` parameter
   - Store as `self.adapter`
   - Get portal name from adapter

2. **Delete methods** (~180 lines):
   - Lines 152-177: `_translate_postal_codes_to_area_ids()`
   - Lines 179-198: `build_willhaben_url()`
   - Lines 200-218: `extract_listing_urls()`
   - Lines 220-227: `extract_listing_id()`
   - Lines 838-913: `_extract_address_from_html()`

3. **Replace method calls** (throughout file):
   ```python
   # Ad filtering (line 242)
   self.adapter.should_filter_ad(html)

   # Address extraction (line 279)
   self.adapter.extract_address_from_html(html, url)

   # Listing ID (line 1117)
   self.adapter.extract_listing_id(url)

   # Crawler config (lines 1127-1131)
   crawler_config = self.adapter.get_crawler_config()
   result = await crawler.arun(url=url, **crawler_config)

   # URL building (line 1220)
   self.adapter.build_search_url(page)

   # Search results crawling (lines 1223-1227)
   crawler_config = self.adapter.get_search_crawler_config()
   result = await crawler.arun(url=url, **crawler_config)

   # Listing URL extraction (line 1235)
   self.adapter.extract_listing_urls(result.html)
   ```

4. **Update main() entry point** (lines 1614-1643):
   ```python
   async def main():
       config = await load_config()
       from portals import get_adapter
       adapter = get_adapter(config)
       scraper = EnhancedApartmentScraper(config, adapter)
       apartments = await scraper.run()
   ```

#### Validation

```bash
# Run existing integration tests
uv run python tests/test_simple.py
uv run python tests/test_single.py

# Full scrape with max_pages=1
uv run python main.py
```

**Expected Outcome**: Identical results to pre-refactor version

---

### Phase 3: Cleanup and Finalization - 1 hour

**Goal**: Remove dead code and finalize migration

#### Tasks

1. **Clean up `models/constants.py`**:
   - Delete lines 194-289 (AREA_ID_TO_LOCATION, PLZ_TO_AREA_ID)
   - Keep all Austrian constants

2. **Update imports in `main.py`**:
   - Add: `from portals.base import PortalAdapter`
   - Remove unused imports

3. **Write unit tests** (`tests/test_portal_adapters.py`):
   ```python
   def test_willhaben_postal_code_translation():
       config = {"portal": "willhaben", "postal_codes": ["1010", "1020"], "filters": {}}
       adapter = WillhabenAdapter(config)
       assert adapter.area_ids == [201, 202]

   def test_willhaben_url_building():
       config = {"portal": "willhaben", "postal_codes": ["1010"], "filters": {"max_price": 150000}}
       adapter = WillhabenAdapter(config)
       url = adapter.build_search_url(page=1)
       assert "areaId=201" in url
       assert "PRICE_TO=150000" in url
   ```

4. **Backward compatibility tests** (`tests/test_backward_compatibility.py`):
   ```python
   def test_legacy_area_ids_config():
       """Old area_ids format still works"""
       config = {"portal": "willhaben", "area_ids": [201, 202], "filters": {}}
       adapter = WillhabenAdapter(config)
       assert adapter.area_ids == [201, 202]
   ```

#### Validation

```bash
uv run pytest tests/ -v
uv run python main.py  # Compare output to baseline
```

---

### Phase 4: ImmobilienScout24 Research and Placeholder - 4 hours

**Goal**: Research Immoscout website and create functional placeholder adapter

#### Research Tasks (2 hours)

**Manual Website Inspection**:

1. **URL Structure Analysis**:
   - Open https://www.immobilienscout24.at in browser
   - Search for apartments in Vienna 1010
   - Inspect search results page (Dev Tools → Network tab)
   - Document:
     - Base URL format
     - Query parameters (location, price, size, page number)
     - Pagination mechanism (page/offset/token?)
     - Example URLs for different searches

2. **Search Results Page**:
   - Inspect HTML structure
   - Check for JSON-LD structured data:
     ```javascript
     // Look for <script type="application/ld+json">
     // Check if @type: "ItemList" exists
     ```
   - Document:
     - Listing URL extraction method (JSON-LD vs CSS selectors vs data-* attributes)
     - Ad/sponsored listing indicators (CSS classes, data attributes, badges)
     - Results container selector (for Playwright wait_for)
     - Lazy loading behavior

3. **Detail Page Structure**:
   - Open a sample apartment listing
   - Inspect HTML
   - Document:
     - Listing ID format in URL
     - Address extraction patterns:
       - JSON-LD address field
       - HTML elements (class names, data attributes)
       - Meta tags
     - Promoted/featured listing indicators
     - Content loading delays

4. **Location System**:
   - Test searches with different postal codes:
     - Single postal code (1010)
     - Multiple postal codes (1010, 1020)
     - City name (Wien)
   - Document:
     - Are postal codes supported directly in URL?
     - Or need translation to region/area IDs?
     - URL encoding requirements

**Research Deliverables**:
- Sample HTML files saved for testing
- URL patterns documented
- CSS selectors identified
- Example curl commands

#### Implementation Tasks (2 hours)

Create `portals/immoscout/adapter.py` with:

**Placeholder Implementation**:
```python
class ImmoscoutAdapter(PortalAdapter):
    """ImmobilienScout24.at portal adapter (PLACEHOLDER - requires research)"""

    def build_search_url(self, page: int = 1, **kwargs) -> str:
        """
        TODO: Research complete URL structure

        Expected format (UNVERIFIED):
        https://www.immobilienscout24.at/regional/wien/wohnung-kaufen?...
        or
        https://www.immobilienscout24.at/suche?postcodes=1010,1020&...
        """
        base_url = "https://www.immobilienscout24.at/regional"
        params = []

        if self.postal_codes:
            params.append(f"postcodes={','.join(str(p) for p in self.postal_codes)}")

        max_price = self.filters.get("max_price")
        if max_price:
            params.append(f"price_max={int(max_price)}")  # TODO: Verify param name

        params.append(f"page={page}")  # TODO: Verify param name

        url = f"{base_url}?{'&'.join(params)}"
        logger.warning(f"ImmoscoutAdapter.build_search_url() is PLACEHOLDER: {url}")
        return url

    def extract_listing_urls(self, html: str) -> List[Dict[str, str]]:
        """
        TODO: Research extraction method

        Possible approaches:
        1. JSON-LD structured data (preferred if available)
        2. CSS selectors for listing cards
        3. data-* attributes
        """
        logger.warning("ImmoscoutAdapter.extract_listing_urls() is PLACEHOLDER - returning empty list")
        return []

    # ... similar placeholder implementations for all methods
```

**Expected Deliverable**:
- Immoscout adapter that instantiates without errors
- All methods implemented with TODO comments
- Warnings logged clearly
- Research findings documented in docstrings

#### Validation

```bash
python -c "from portals import get_adapter; adapter = get_adapter({'portal': 'immoscout', 'postal_codes': ['1010'], 'filters': {}}); print(adapter.get_portal_name())"
```

Expected output: "immoscout" with no errors (warnings OK)

---

### Phase 5: Multi-Portal Support (Sequential Execution) - 3 hours

**Goal**: Enable `portal: "both"` configuration with sequential execution

#### Tasks

1. **Implement `portals/multi_portal.py`**:
   ```python
   class MultiPortalAdapter(PortalAdapter):
       """Meta-adapter for sequential multi-portal execution"""

       def __init__(self, config: Dict[str, Any]):
           super().__init__(config)
           from portals.willhaben.adapter import WillhabenAdapter
           from portals.immoscout.adapter import ImmoscoutAdapter

           self.adapters = [
               WillhabenAdapter(config),
               ImmoscoutAdapter(config),
           ]
           self.current_adapter_index = 0

       def get_current_adapter(self) -> PortalAdapter:
           """Return the currently active adapter"""
           return self.adapters[self.current_adapter_index]

       def switch_to_next_portal(self) -> bool:
           """
           Switch to next portal.

           Returns:
               True if switched, False if no more portals
           """
           self.current_adapter_index += 1
           if self.current_adapter_index >= len(self.adapters):
               return False

           portal_name = self.get_current_adapter().get_portal_name()
           logger.info(f"=== Switching to portal: {portal_name} ===")
           return True

       # Delegate all methods to current adapter
       def build_search_url(self, page: int = 1, **kwargs) -> str:
           return self.get_current_adapter().build_search_url(page, **kwargs)

       # ... (delegate all other abstract methods similarly)
   ```

2. **Modify `EnhancedApartmentScraper.run()` in `main.py`**:
   ```python
   async def run(self) -> List[ApartmentMetadata]:
       """Run scraping for single or multiple portals"""

       # Check if multi-portal mode
       if isinstance(self.adapter, MultiPortalAdapter):
           all_apartments = []

           # Sequential execution: scrape each portal in order
           while True:
               portal_name = self.adapter.get_current_adapter().get_portal_name()
               logger.info(f"=== Starting scrape for portal: {portal_name} ===")

               # Run scraping for current portal
               portal_apartments = await self._run_single_portal()
               all_apartments.extend(portal_apartments)

               logger.info(f"=== Completed portal: {portal_name} ({len(portal_apartments)} apartments) ===")

               # Switch to next portal
               if not self.adapter.switch_to_next_portal():
                   break

           logger.info(f"=== Multi-portal scraping complete: {len(all_apartments)} total apartments ===")
           return all_apartments

       else:
           # Single portal mode
           return await self._run_single_portal()

   async def _run_single_portal(self) -> List[ApartmentMetadata]:
       """Run scraping for a single portal (existing run() logic moved here)"""
       # ... current implementation ...
   ```

3. **Output organization**:
   - Apartments from both portals merged into single ranking
   - `source_portal` field differentiates origin
   - Summary report shows mixed results sorted by investment_score
   - PDF report includes top N from combined ranking

#### Validation

```bash
# Update config.json: "portal": "both"
uv run python main.py

# Check output structure
ls -la output/apartments_*/
cat output/apartments_*/summary.md | head -50

# Verify mixed portal sources
grep "source_portal" output/apartments_*/*.md | head -20
```

Expected: Willhaben apartments scraped first, then Immoscout (placeholder returns empty), merged in summary

---

### Phase 6: Documentation and Testing - 2 hours

**Goal**: Comprehensive documentation and final validation

#### Documentation Tasks

1. **Update `README.md`**:
   - Add multi-portal configuration examples
   - Document all three portal modes (willhaben, immoscout, both)
   - Add troubleshooting section for multi-portal issues
   - Update setup instructions

2. **Update `CLAUDE.md`**:
   - Add multi-portal architecture section
   - Document portal adapter pattern
   - Update project structure diagram
   - Add development guide for adding new portals
   - Update "Common Development Tasks" section

3. **Update this file (`immoscout24_implementation_details/Plan.md`)**:
   - Add research findings from Phase 4
   - Document actual Immoscout URL patterns
   - Include example HTML snippets
   - Add curl commands for testing

#### Testing Tasks

1. **Unit tests** (`tests/test_portal_adapters.py`):
   ```bash
   uv run pytest tests/test_portal_adapters.py -v
   ```

2. **Backward compatibility tests** (`tests/test_backward_compatibility.py`):
   ```bash
   uv run pytest tests/test_backward_compatibility.py -v
   ```

3. **Integration tests**:
   ```bash
   # Test each portal mode
   uv run python main.py  # Willhaben only

   # Change config: "portal": "immoscout" (will show placeholder warnings)
   uv run python main.py

   # Change config: "portal": "both"
   uv run python main.py
   ```

4. **Output validation**:
   - Compare Willhaben-only output to baseline (pre-refactor)
   - Verify summary.md format is correct
   - Check PDF generation works
   - Validate YAML frontmatter in markdown files
   - Ensure investment scores are calculated correctly

---

## Configuration Design

### Single Portal Configuration

**Willhaben**:
```json
{
  "portal": "willhaben",
  "postal_codes": ["1010", "1020", "9020"],
  "max_pages": 1,
  "llm_settings": { ... },
  "filters": { "max_price": 150000, ... },
  "analysis": { ... },
  "output": { ... },
  "rate_limiting": { ... }
}
```

**ImmobilienScout24**:
```json
{
  "portal": "immoscout",
  "postal_codes": ["1010", "1020"],
  "max_pages": 1,
  "llm_settings": { ... },
  "filters": { ... },
  "analysis": { ... },
  "output": { ... },
  "rate_limiting": { ... }
}
```

**Note**: Configuration is identical except for `portal` field. This is intentional - all Austrian-specific settings (postal codes, rent estimates, transaction costs) are portal-agnostic.

### Multi-Portal Configuration

```json
{
  "portal": "both",
  "postal_codes": ["1010", "1020"],
  "max_pages": 1,
  "llm_settings": { ... },
  "filters": { ... },
  "analysis": { ... },
  "output": { ... },
  "rate_limiting": { ... }
}
```

**Behavior**:
- Scrapes Willhaben first, then ImmobilienScout24 (sequential)
- Apartments from both portals merged into single ranking
- Summary report shows combined top N sorted by investment_score
- Output folder structure:
  ```
  output/apartments_2025-12-13-163000/
  ├── 2025-12-13_8.5_Wien_3_120k.md     (Willhaben)
  ├── 2025-12-13_8.3_Wien_5_135k.md     (Immoscout)
  ├── 2025-12-13_7.9_Klagenfurt_95k.md  (Willhaben)
  ├── summary.md                        (Combined ranking)
  └── investment_summary.pdf            (Top 20 from both portals)
  ```

### Future Enhancement: Portal-Specific Settings

If portals need different configurations in the future:

```json
{
  "portal": "both",

  "willhaben_settings": {
    "postal_codes": ["1010", "1020"],
    "max_price": 150000
  },

  "immoscout_settings": {
    "postal_codes": ["1010", "1020", "1030"],
    "max_price": 200000
  },

  "shared_settings": {
    "llm_settings": { ... },
    "analysis": { ... },
    "output": { ... }
  }
}
```

**Recommendation**: Only implement this if absolutely necessary. Keep it simple initially with shared settings.

---

## Execution Strategy Analysis

### Sequential Execution (RECOMMENDED)

**Implementation**: `MultiPortalAdapter` with adapter switching

**Pros**:
- ✅ **Simple error handling**: One portal fails → continue with next
- ✅ **Easy rate limiting**: No coordination needed between portals
- ✅ **Lower memory usage**: One Playwright browser instance at a time (~200MB)
- ✅ **Predictable resource usage**: CPU/memory profile identical to single portal
- ✅ **Clear logging**: One portal at a time, easy to debug
- ✅ **Error isolation**: Portal failures are independent

**Cons**:
- ❌ **Slower total time**: 2x duration if both portals have equal listings
- ❌ **Blocking behavior**: Second portal waits for first to complete
- ❌ **Underutilized resources**: CPU idle during network I/O waits

**Performance Example** (max_pages=1):
- Willhaben: ~1.5 minutes
- Immoscout: ~1.5 minutes
- **Total: ~3 minutes** (sequential)

**Use Case Fit for noessi-crawl**: ✅ **EXCELLENT**

Reasons:
1. Browser automation is already I/O-bound (network + rendering waits)
2. Rate limiting is important for polite scraping (avoid blocking)
3. Typical usage has `max_pages=1` (minimal difference vs parallel)
4. Memory constraints on typical development machines
5. Error isolation valuable for reliability

---

### Parallel Execution (Future Enhancement)

**Implementation**: `asyncio.gather()` with multiple scraper instances

**Pros**:
- ✅ **Faster total time**: Both portals run simultaneously
- ✅ **Better resource utilization**: CPU/network used efficiently
- ✅ **Independent progress**: One portal's slowness doesn't block the other

**Cons**:
- ❌ **Complex error handling**: Need `asyncio.gather(..., return_exceptions=True)`
- ❌ **Rate limiting coordination**: Both portals hitting network simultaneously
- ❌ **Memory overhead**: 2x browser instances (~400MB), 2x apartments in memory
- ❌ **Harder debugging**: Interleaved logs from both portals
- ❌ **Resource exhaustion risk**: Playwright browsers are resource-heavy

**Performance Example** (max_pages=1):
- Both portals: ~1.5 minutes (parallelized)
- **Total: ~1.5 minutes** (parallel)
- **Speedup**: 2x vs sequential

**Use Case Fit for noessi-crawl**: ⚠️ **QUESTIONABLE**

Reasons:
1. May hit browser resource limits (2+ Playwright instances)
2. Rate limiting becomes complex (need global throttle)
3. Minimal benefit for `max_pages=1` (current config)
4. Increased complexity not justified for small performance gain

**Recommendation**:

Implement **sequential execution initially**. Add parallel execution as an **opt-in feature** later if performance becomes critical:

```json
{
  "portal": "both",
  "execution_mode": "sequential",  // or "parallel" (future enhancement)
  ...
}
```

---

## Critical Files Reference

### Files to Create

| File | Purpose | LOC Estimate |
|------|---------|--------------|
| `portals/__init__.py` | Factory function `get_adapter()` | 50 |
| `portals/base.py` | Abstract `PortalAdapter` base class | 150 |
| `portals/willhaben/__init__.py` | Exports | 10 |
| `portals/willhaben/adapter.py` | `WillhabenAdapter` implementation | 200 |
| `portals/willhaben/constants.py` | Moved from `models/constants.py` | 100 |
| `portals/immoscout/__init__.py` | Exports | 10 |
| `portals/immoscout/adapter.py` | Placeholder + implementation | 150 |
| `portals/immoscout/constants.py` | Immoscout-specific mappings (TBD) | 50 |
| `portals/multi_portal.py` | Sequential execution | 100 |
| `tests/test_portal_adapters.py` | Unit tests for adapters | 120 |
| `tests/test_backward_compatibility.py` | Backward compatibility tests | 80 |
| **Total New Files** | | **~1,020 LOC** |

### Files to Modify

| File | Changes | LOC Impact |
|------|---------|-----------|
| `main.py` | Add imports, adapter DI, remove Willhaben methods | **-160 LOC** |
| `models/constants.py` | Remove PLZ_TO_AREA_ID, AREA_ID_TO_LOCATION | **-96 LOC** |
| `config.json` | Optional: Add comments for supported portals | **0 LOC** |
| `README.md` | Add multi-portal documentation | **+50 LOC** |
| `CLAUDE.md` | Document portal adapter pattern | **+100 LOC** |

**Net LOC Change**: ~1,020 new - 256 removed + 150 docs = **+914 LOC total**

### Files Unchanged (100% Portal-Agnostic)

- `models/apartment.py` - Data model
- `utils/extractors.py` - Austrian regex patterns
- `utils/address_parser.py` - Austrian address parsing
- `llm/extractor.py` - LLM extraction
- `llm/analyzer.py` - Investment analysis
- `llm/summarizer.py` - LLM summarization
- `utils/markdown_generator.py` - Markdown generation
- `utils/pdf_generator.py` - PDF generation
- `utils/translations.py` - German translations
- `utils/top_n_tracker.py` - Top N tracking

**Total Unchanged**: ~2,000 LOC (no refactoring needed)

---

## Risk Mitigation

### Backward Compatibility

**Guarantee**: Existing Willhaben scraping must work **exactly** as before after refactoring.

**Strategies**:

1. **Configuration Compatibility**:
   - Support both `postal_codes` (new, user-friendly) and `area_ids` (legacy, direct)
   - Never break existing config.json files
   - Validate with legacy config during testing

2. **Test-Driven Refactoring**:
   - Write backward compatibility tests **before** making changes
   - Run tests after every phase
   - Compare output to baseline (pre-refactor run)

3. **Gradual Migration**:
   - Phase 1: Create adapters without touching main.py
   - Phase 2: Integrate adapters, keep old code temporarily
   - Phase 3: Delete old code only after validation

4. **Validation Checkpoints**:
   - After Phase 2: Run full scrape, compare apartment count and extraction quality
   - After Phase 3: Run all tests, compare summary report format
   - Before merging: Final comparison with baseline

**Validation Command**:
```bash
# Before refactoring
uv run python main.py > baseline_output.log 2>&1

# After each phase
uv run python main.py > refactored_output.log 2>&1

# Compare
diff baseline_output.log refactored_output.log
```

---

### ImmobilienScout24 Implementation

**Risk**: Immoscout website structure may differ significantly from expectations.

**Mitigation**:

1. **Placeholder Approach**:
   - Create working placeholder that logs warnings instead of failing silently
   - Return empty results gracefully
   - Don't crash entire scrape if Immoscout fails

2. **Iterative Implementation**:
   - Phase 4: Research only (no functional code required)
   - Future: Implement in separate PR with dedicated testing
   - Allow time for iteration based on research findings

3. **Graceful Degradation**:
   - If Immoscout adapter fails during "both" mode, continue with Willhaben
   - Log errors clearly with ERROR level
   - Return partial results instead of crashing

**Example Error Handling**:
```python
try:
    portal_apartments = await self._run_single_portal()
    all_apartments.extend(portal_apartments)
except Exception as e:
    portal_name = self.adapter.get_current_adapter().get_portal_name()
    logger.error(f"Portal {portal_name} failed: {e}", exc_info=True)
    # Continue with next portal instead of crashing
```

---

### Multi-Portal Execution

**Risk**: Sequential execution may seem slower to users accustomed to single-portal speed.

**Mitigation**:

1. **Clear Logging**:
   ```
   [INFO] === Starting scrape for portal: willhaben ===
   [INFO] Portal: willhaben - Page 1: 25 apartments (Total: 25)
   [INFO] Portal: willhaben - Page 2: 24 apartments (Total: 49)
   [INFO] === Completed portal: willhaben (49 apartments) ===
   [INFO] === Switching to portal: immoscout ===
   [INFO] === Starting scrape for portal: immoscout ===
   [INFO] Portal: immoscout - Page 1: 20 apartments (Total: 69)
   [INFO] === Completed portal: immoscout (20 apartments) ===
   [INFO] === Multi-portal scraping complete: 69 total apartments ===
   ```

2. **Progress Indicators**:
   - Show combined total in logs to demonstrate value
   - Update progress after each portal completes
   - Clearly indicate when switching portals

3. **Documentation**:
   - Explain sequential vs parallel tradeoffs in README
   - Document that sequential is intentional for reliability
   - Mention parallel execution as future enhancement

4. **Performance Transparency**:
   - Log time taken for each portal
   - Show speedup would be minimal for typical usage (`max_pages=1`)

---

## Success Criteria

### Phase Completion Checklist

**Phase 1-3 (Willhaben Refactoring)**:
- [ ] All existing tests pass (`uv run pytest tests/ -v`)
- [ ] Backward compatibility tests pass
- [ ] Single scrape produces identical results to pre-refactor version
- [ ] No new warnings or errors in logs
- [ ] `WillhabenAdapter` unit tests pass
- [ ] Code coverage remains ≥ current level

**Phase 4 (Immoscout Placeholder)**:
- [ ] `ImmoscoutAdapter` can be instantiated
- [ ] Factory function handles "immoscout" portal
- [ ] Placeholder methods return empty/safe defaults with warnings
- [ ] Research notes documented in code comments and this file

**Phase 5 (Multi-Portal)**:
- [ ] Config with `portal: "both"` runs without errors
- [ ] Summary report merges apartments from all portals
- [ ] PDF report shows combined rankings
- [ ] Logs clearly indicate portal switching
- [ ] Graceful error handling if one portal fails

**Phase 6 (Documentation)**:
- [ ] `README.md` updated with multi-portal examples
- [ ] `CLAUDE.md` reflects new architecture
- [ ] All new code has comprehensive docstrings
- [ ] This file updated with research findings

---

### Quality Metrics

**Code Quality**:
- **Maintainability**: Portal-specific code isolated in adapters (✅)
- **Testability**: Each adapter testable in isolation (✅)
- **Extensibility**: Adding new portal requires ~200 LOC, no core changes (✅)
- **Documentation**: Every public method has docstring (✅)

**Performance**:
- **No Regression**: Willhaben scraping speed unchanged (✅)
- **Acceptable Overhead**: Multi-portal sequential execution ≤ 2x single portal time (✅)
- **Memory Usage**: No significant increase for single portal mode (✅)

**Reliability**:
- **Error Isolation**: One portal's failure doesn't crash the other (✅)
- **Graceful Degradation**: Missing features logged as warnings, not errors (✅)
- **Backward Compatibility**: All existing configs work without changes (✅)

---

## Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **1. Foundation** | 4 hours | Portal adapter infrastructure, WillhabenAdapter |
| **2. Integration** | 3 hours | main.py refactored with dependency injection |
| **3. Cleanup** | 1 hour | Dead code removed, tests written |
| **4. Immoscout Research** | 4 hours | Placeholder adapter + research documentation |
| **5. Multi-Portal** | 3 hours | Sequential execution working |
| **6. Documentation** | 2 hours | README, CLAUDE.md, implementation details updated |
| **Total** | **17 hours** | **Production-ready multi-portal scraper** |

**Realistic Timeline**: 2-3 days for one developer

**Notes**:
- Assumes no major blockers during Immoscout research
- Includes testing and validation time
- Allows for iteration and debugging
- Conservative estimates (may be faster for experienced developer)

---

## Next Steps

1. **Current Session** (COMPLETED):
   - ✅ Created `immoscout24_implementation_details/` folder
   - ✅ Created `Plan.md` (this file)
   - ⏳ Create `Todos.md` with task tracking

2. **Next Session** (Phase 1):
   - Create `portals/` folder structure
   - Implement `PortalAdapter` base class
   - Extract Willhaben logic into `WillhabenAdapter`
   - Create factory function

3. **Subsequent Sessions**:
   - Follow phases 2-6 sequentially
   - Update `Todos.md` after each task completion
   - Document research findings in this file
   - Validate at each checkpoint

---

## Research Notes (To Be Filled During Phase 4)

### ImmobilienScout24 URL Patterns

**Search URL Structure**:
```
TODO: Document actual URL format after research
Example: https://www.immobilienscout24.at/...
```

**Parameters**:
- Location: TBD
- Price filter: TBD
- Pagination: TBD

### Listing Extraction Method

**JSON-LD Availability**: TBD

**Alternative Extraction Methods**: TBD

### Ad Filtering Indicators

**Sponsored Listing Markers**: TBD

### Example HTML Snippets

```html
<!-- TODO: Paste sample HTML from search results page -->
```

```html
<!-- TODO: Paste sample HTML from detail page -->
```

### Curl Commands for Testing

```bash
# TODO: Add curl commands discovered during research
curl -A "Mozilla/5.0" "https://www.immobilienscout24.at/..." > immoscout_search.html
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Status**: Initial planning complete, ready for implementation
